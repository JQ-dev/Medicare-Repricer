"""
Main Medicare repricing interface.

Provides the primary interface for repricing claims to Medicare rates.
"""

from typing import Optional, List
from datetime import datetime
from pathlib import Path

from .models import Claim, RepricedClaim, RepricedClaimLine
from .fee_schedule import MedicareFeeSchedule, create_default_fee_schedule
from .calculator import MedicareCalculator


class MedicareRepricer:
    """
    Main interface for repricing medical claims to Medicare rates.

    This class orchestrates the repricing process by:
    1. Loading Medicare fee schedules (RVU and GPCI data)
    2. Processing claim lines through the pricing calculator
    3. Applying multiple procedure payment reductions
    4. Generating detailed repriced claim objects

    Example:
        >>> repricer = MedicareRepricer()
        >>> claim = Claim(...)
        >>> repriced = repricer.reprice_claim(claim)
        >>> print(f"Total allowed: ${repriced.total_allowed:.2f}")
    """

    def __init__(
        self,
        fee_schedule: Optional[MedicareFeeSchedule] = None,
        data_directory: Optional[Path] = None
    ):
        """
        Initialize the Medicare repricer.

        Args:
            fee_schedule: Optional pre-configured fee schedule. If not provided,
                         uses default sample data.
            data_directory: Optional directory containing fee schedule data files.
                          If provided, loads data from this directory.
        """
        if fee_schedule:
            self.fee_schedule = fee_schedule
        elif data_directory:
            self.fee_schedule = MedicareFeeSchedule()
            self.fee_schedule.load_from_directory(data_directory)
        else:
            # Use default sample fee schedule
            self.fee_schedule = create_default_fee_schedule()

        self.calculator = MedicareCalculator(self.fee_schedule)

    def reprice_claim(self, claim: Claim) -> RepricedClaim:
        """
        Reprice a complete claim to Medicare rates.

        This method:
        1. Validates the claim structure
        2. Processes each line through the Medicare calculator
        3. Applies multiple procedure payment reductions
        4. Calculates totals
        5. Returns a detailed repriced claim

        Args:
            claim: Input claim with diagnosis codes and procedure lines

        Returns:
            RepricedClaim with Medicare allowed amounts and calculation details

        Raises:
            ValueError: If claim validation fails or required data is missing
        """
        # Validate claim
        self._validate_claim(claim)

        # Determine if we need to apply MPPR
        # Group procedures by same-day, same-specialty rules
        # For simplicity, we'll apply MPPR to all procedures in order
        mppr_procedures = self._identify_mppr_procedures(claim.lines)

        # Process each line
        repriced_lines: List[RepricedClaimLine] = []

        for line in claim.lines:
            try:
                # Determine if this is subject to MPPR
                is_multiple = len(mppr_procedures) > 1 and line.procedure_code in mppr_procedures
                procedure_rank = mppr_procedures.index(line.procedure_code) + 1 if is_multiple else 1

                # Calculate Medicare allowed amount
                allowed_amount, details = self.calculator.calculate_allowed_amount(
                    procedure_code=line.procedure_code,
                    place_of_service=line.place_of_service,
                    locality=line.locality,
                    modifier=line.modifier,
                    units=line.units,
                    is_multiple_procedure=is_multiple,
                    procedure_rank=procedure_rank
                )

                # Create repriced line
                repriced_line = RepricedClaimLine(
                    line_number=line.line_number,
                    procedure_code=line.procedure_code,
                    modifier=line.modifier,
                    place_of_service=line.place_of_service,
                    locality=line.locality,
                    units=line.units,
                    work_rvu=details["work_rvu"],
                    pe_rvu=details["pe_rvu"],
                    mp_rvu=details["mp_rvu"],
                    work_gpci=details["work_gpci"],
                    pe_gpci=details["pe_gpci"],
                    mp_gpci=details["mp_gpci"],
                    conversion_factor=details["conversion_factor"],
                    medicare_allowed=allowed_amount,
                    adjustment_reason="; ".join(details["notes"]) if details["notes"] else None
                )

                repriced_lines.append(repriced_line)

            except ValueError as e:
                # Create a repriced line with error information
                repriced_line = RepricedClaimLine(
                    line_number=line.line_number,
                    procedure_code=line.procedure_code,
                    modifier=line.modifier,
                    place_of_service=line.place_of_service,
                    locality=line.locality,
                    units=line.units,
                    work_rvu=0.0,
                    pe_rvu=0.0,
                    mp_rvu=0.0,
                    work_gpci=0.0,
                    pe_gpci=0.0,
                    mp_gpci=0.0,
                    conversion_factor=self.fee_schedule.conversion_factor,
                    medicare_allowed=0.0,
                    adjustment_reason=f"ERROR: {str(e)}"
                )
                repriced_lines.append(repriced_line)

        # Calculate totals
        total_allowed = sum(line.medicare_allowed for line in repriced_lines)

        # Create repriced claim
        repriced_claim = RepricedClaim(
            claim_id=claim.claim_id,
            patient_id=claim.patient_id,
            diagnosis_codes=claim.diagnosis_codes,
            lines=repriced_lines,
            total_allowed=total_allowed,
            repricing_date=datetime.now().isoformat()
        )

        # Add informational notes
        repriced_claim.add_note(f"Repriced using Medicare Conversion Factor: ${self.fee_schedule.conversion_factor}")
        if len(mppr_procedures) > 1:
            repriced_claim.add_note(f"MPPR applied to {len(mppr_procedures)} procedures")

        return repriced_claim

    def reprice_claims(self, claims: List[Claim]) -> List[RepricedClaim]:
        """
        Reprice multiple claims.

        Args:
            claims: List of claims to reprice

        Returns:
            List of repriced claims
        """
        return [self.reprice_claim(claim) for claim in claims]

    def _validate_claim(self, claim: Claim) -> None:
        """
        Validate claim structure and data.

        Args:
            claim: Claim to validate

        Raises:
            ValueError: If claim validation fails
        """
        if not claim.claim_id or not claim.claim_id.strip():
            raise ValueError("Claim ID is required")

        if not claim.diagnosis_codes:
            raise ValueError("At least one diagnosis code is required")

        if not claim.lines:
            raise ValueError("At least one claim line is required")

        # Validate line numbers are sequential and unique
        line_numbers = [line.line_number for line in claim.lines]
        if len(line_numbers) != len(set(line_numbers)):
            raise ValueError("Claim line numbers must be unique")

    def _identify_mppr_procedures(self, lines: List) -> List[str]:
        """
        Identify procedures subject to Multiple Procedure Payment Reduction.

        In a full implementation, this would consider:
        - Same-day procedures
        - Same specialty
        - Procedure indicators
        - Complexity ranking

        For this implementation, we'll use a simplified approach:
        - Sort by RVU value (descending)
        - Return procedures with MPPR indicator

        Args:
            lines: List of claim lines

        Returns:
            List of procedure codes in MPPR order (highest to lowest)
        """
        # Get unique procedure codes
        procedures = []
        for line in lines:
            rvu = self.fee_schedule.get_rvu(line.procedure_code, line.modifier)
            if rvu and rvu.mp_indicator == 2:  # Subject to MPPR
                # Calculate total RVU for ranking
                is_facility = self.calculator._is_facility_setting(line.place_of_service)
                total_rvu = (
                    (rvu.work_rvu_f if is_facility else rvu.work_rvu_nf) +
                    (rvu.pe_rvu_f if is_facility else rvu.pe_rvu_nf) +
                    (rvu.mp_rvu_f if is_facility else rvu.mp_rvu_nf)
                )
                procedures.append((line.procedure_code, total_rvu))

        # Sort by total RVU (descending)
        procedures.sort(key=lambda x: x[1], reverse=True)

        return [code for code, _ in procedures]

    def get_procedure_info(self, procedure_code: str, modifier: Optional[str] = None) -> Optional[dict]:
        """
        Get detailed information about a procedure code.

        Args:
            procedure_code: CPT or HCPCS code
            modifier: Optional modifier

        Returns:
            Dictionary with procedure information, or None if not found
        """
        rvu = self.fee_schedule.get_rvu(procedure_code, modifier)
        if not rvu:
            return None

        return {
            "procedure_code": rvu.procedure_code,
            "modifier": rvu.modifier,
            "description": rvu.description,
            "work_rvu_non_facility": rvu.work_rvu_nf,
            "pe_rvu_non_facility": rvu.pe_rvu_nf,
            "mp_rvu_non_facility": rvu.mp_rvu_nf,
            "work_rvu_facility": rvu.work_rvu_f,
            "pe_rvu_facility": rvu.pe_rvu_f,
            "mp_rvu_facility": rvu.mp_rvu_f,
            "mppr_indicator": rvu.mp_indicator,
            "conversion_factor": self.fee_schedule.conversion_factor
        }

    def get_locality_info(self, locality: str) -> Optional[dict]:
        """
        Get GPCI information for a locality.

        Args:
            locality: Medicare locality code

        Returns:
            Dictionary with locality information, or None if not found
        """
        gpci = self.fee_schedule.get_gpci(locality)
        if not gpci:
            return None

        return {
            "locality": gpci.locality,
            "locality_name": gpci.locality_name,
            "work_gpci": gpci.work_gpci,
            "pe_gpci": gpci.pe_gpci,
            "mp_gpci": gpci.mp_gpci
        }
