"""
Medicare pricing calculation engine.

Implements official Medicare payment formulas including:
- RBRVS-based pricing
- GPCI adjustments
- Multiple Procedure Payment Reduction (MPPR)
- Modifier adjustments
"""

from typing import Optional, Tuple, List
from .fee_schedule import MedicareFeeSchedule, RVUData, GPCIData


class MedicareCalculator:
    """
    Calculates Medicare allowed amounts using the Physician Fee Schedule formula.

    Formula:
    Payment = [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × CF

    Where:
    - RVU = Relative Value Unit
    - GPCI = Geographic Practice Cost Index
    - CF = Conversion Factor
    - PE = Practice Expense
    - MP = Malpractice
    """

    def __init__(self, fee_schedule: MedicareFeeSchedule):
        """
        Initialize calculator with a fee schedule.

        Args:
            fee_schedule: MedicareFeeSchedule instance with RVU and GPCI data
        """
        self.fee_schedule = fee_schedule

    def calculate_allowed_amount(
        self,
        procedure_code: str,
        place_of_service: str,
        locality: str,
        modifiers: Optional[List[str]] = None,
        units: int = 1,
        is_multiple_procedure: bool = False,
        procedure_rank: int = 1,
    ) -> Tuple[float, dict]:
        """
        Calculate Medicare allowed amount for a procedure.

        Args:
            procedure_code: CPT or HCPCS code
            place_of_service: Two-digit POS code (11=Office, 22=Outpatient, etc.)
            locality: Medicare locality code
            modifiers: Optional list of procedure modifiers (up to 2)
            units: Number of units
            is_multiple_procedure: Whether this is part of multiple procedures
            procedure_rank: Rank when multiple procedures (1=highest, 2=second, etc.)

        Returns:
            Tuple of (allowed_amount, calculation_details)

        Raises:
            ValueError: If procedure code or locality not found
        """
        # Get RVU data - use first modifier for lookup if available
        first_modifier = modifiers[0] if modifiers and len(modifiers) > 0 else None
        rvu = self.fee_schedule.get_rvu(procedure_code, first_modifier)
        if not rvu:
            raise ValueError(f"Procedure code {procedure_code} not found in fee schedule")

        # Get GPCI data
        gpci = self.fee_schedule.get_gpci(locality)
        if not gpci:
            # Fall back to national average
            gpci = self.fee_schedule.get_gpci("00")
            if not gpci:
                raise ValueError(f"Locality {locality} not found and no default available")

        # Determine facility vs non-facility based on place of service
        is_facility = self._is_facility_setting(place_of_service)

        # Get appropriate RVUs
        work_rvu = rvu.work_rvu_f if is_facility else rvu.work_rvu_nf
        pe_rvu = rvu.pe_rvu_f if is_facility else rvu.pe_rvu_nf
        mp_rvu = rvu.mp_rvu_f if is_facility else rvu.mp_rvu_nf

        # Apply modifier adjustments (sequentially for multiple modifiers)
        work_rvu, pe_rvu, mp_rvu, modifier_notes = self._apply_modifier_adjustments(
            work_rvu, pe_rvu, mp_rvu, modifiers
        )

        # Calculate base payment
        work_component = work_rvu * gpci.work_gpci
        pe_component = pe_rvu * gpci.pe_gpci
        mp_component = mp_rvu * gpci.mp_gpci

        base_payment = (work_component + pe_component + mp_component) * self.fee_schedule.conversion_factor

        # Apply Multiple Procedure Payment Reduction (MPPR)
        mppr_adjustment = 1.0
        mppr_note = None

        if is_multiple_procedure and procedure_rank > 1 and rvu.mp_indicator == 2:
            # Standard MPPR: 50% reduction for second and subsequent procedures
            mppr_adjustment = 0.50
            mppr_note = f"MPPR 50% applied (procedure rank {procedure_rank})"

        # Calculate final allowed amount
        allowed_amount = base_payment * mppr_adjustment * units

        # Build calculation details
        details = {
            "procedure_code": procedure_code,
            "modifiers": modifiers,
            "work_rvu": work_rvu,
            "pe_rvu": pe_rvu,
            "mp_rvu": mp_rvu,
            "work_gpci": gpci.work_gpci,
            "pe_gpci": gpci.pe_gpci,
            "mp_gpci": gpci.mp_gpci,
            "conversion_factor": self.fee_schedule.conversion_factor,
            "base_payment": base_payment,
            "mppr_adjustment": mppr_adjustment,
            "units": units,
            "allowed_amount": allowed_amount,
            "is_facility": is_facility,
            "locality": locality,
            "locality_name": gpci.locality_name,
            "notes": []
        }

        # Add modifier notes
        if modifier_notes:
            details["notes"].extend(modifier_notes)
        if mppr_note:
            details["notes"].append(mppr_note)

        return allowed_amount, details

    def _is_facility_setting(self, place_of_service: str) -> bool:
        """
        Determine if place of service is a facility setting.

        Facility settings (partial list):
        - 21: Inpatient Hospital
        - 22: Outpatient Hospital
        - 23: Emergency Room - Hospital
        - 24: Ambulatory Surgical Center
        - 51: Inpatient Psychiatric Facility
        - 52: Psychiatric Facility - Partial Hospitalization
        - 53: Community Mental Health Center
        - 56: Psychiatric Residential Treatment Center
        - 61: Comprehensive Inpatient Rehabilitation Facility

        Non-facility settings:
        - 11: Office
        - 12: Home
        - 13: Assisted Living Facility
        - 15: Mobile Unit
        - 49: Independent Clinic
        - etc.

        Args:
            place_of_service: Two-digit POS code

        Returns:
            True if facility setting, False otherwise
        """
        facility_pos_codes = {
            "21", "22", "23", "24", "26", "31", "34",
            "51", "52", "53", "56", "61"
        }
        return place_of_service in facility_pos_codes

    def _apply_modifier_adjustments(
        self,
        work_rvu: float,
        pe_rvu: float,
        mp_rvu: float,
        modifiers: Optional[List[str]]
    ) -> Tuple[float, float, float, List[str]]:
        """
        Apply RVU adjustments based on modifiers.

        Common modifiers:
        - 26: Professional component only (no PE)
        - TC: Technical component only (no work or MP)
        - 50: Bilateral procedure (150% payment)
        - 51: Multiple procedures (handled separately via MPPR)
        - 52: Reduced services (typically 50% reduction)
        - 53: Discontinued procedure (variable reduction)

        Args:
            work_rvu: Work RVU
            pe_rvu: Practice Expense RVU
            mp_rvu: Malpractice RVU
            modifiers: List of procedure modifiers (up to 2)

        Returns:
            Tuple of (adjusted_work_rvu, adjusted_pe_rvu, adjusted_mp_rvu, notes_list)
        """
        notes = []

        if not modifiers:
            return work_rvu, pe_rvu, mp_rvu, notes

        # Apply modifiers sequentially
        for modifier in modifiers:
            if not modifier:
                continue

            modifier = modifier.upper()

            if modifier == "26":
                # Professional component only - no practice expense
                pe_rvu = 0.0
                notes.append("Professional component only (modifier 26)")

            elif modifier == "TC":
                # Technical component only - no work or malpractice
                work_rvu = 0.0
                mp_rvu = 0.0
                notes.append("Technical component only (modifier TC)")

            elif modifier == "50":
                # Bilateral procedure - 150% payment
                work_rvu *= 1.5
                pe_rvu *= 1.5
                mp_rvu *= 1.5
                notes.append("Bilateral procedure (modifier 50) - 150% payment")

            elif modifier == "52":
                # Reduced services - 50% reduction (approximate)
                work_rvu *= 0.5
                pe_rvu *= 0.5
                mp_rvu *= 0.5
                notes.append("Reduced services (modifier 52) - 50% reduction")

            elif modifier == "53":
                # Discontinued procedure - typically 50% reduction
                work_rvu *= 0.5
                pe_rvu *= 0.5
                mp_rvu *= 0.5
                notes.append("Discontinued procedure (modifier 53) - 50% reduction")

            elif modifier == "76" or modifier == "77":
                # Repeat procedure - full payment (no adjustment)
                notes.append(f"Repeat procedure (modifier {modifier}) - full payment")

            elif modifier == "59" or modifier == "XS" or modifier == "XU" or modifier == "XP" or modifier == "XE":
                # Distinct procedural service - no payment adjustment
                notes.append(f"Distinct procedural service (modifier {modifier})")

        return work_rvu, pe_rvu, mp_rvu, notes
