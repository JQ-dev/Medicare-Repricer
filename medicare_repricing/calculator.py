"""
Medicare pricing calculation engine.

Implements official Medicare payment formulas including:
- RBRVS-based pricing
- GPCI adjustments
- Multiple Procedure Payment Reduction (MPPR)
- Modifier adjustments
"""

from typing import Optional, Tuple, List
from .fee_schedule import MedicareFeeSchedule, RVUData, GPCIData, AnesthesiaBaseUnitData, AnesthesiaData
import math


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


class AnesthesiaCalculator:
    """
    Calculates Medicare allowed amounts for anesthesia services.

    Formula:
    Payment = (Base Units + Time Units + Modifying Units) × Conversion Factor

    Where:
    - Base Units = Procedure complexity (from ASA/CMS crosswalk)
    - Time Units = Anesthesia time in minutes ÷ 15 (rounded up)
    - Modifying Units = Additional units for qualifying circumstances, physical status, etc.
    - Conversion Factor = Locality-specific anesthesia conversion factor
    """

    def __init__(self, fee_schedule: MedicareFeeSchedule):
        """
        Initialize calculator with a fee schedule.

        Args:
            fee_schedule: MedicareFeeSchedule instance with anesthesia data
        """
        self.fee_schedule = fee_schedule

    def calculate_allowed_amount(
        self,
        procedure_code: str,
        contractor: str,
        locality: str,
        time_minutes: int,
        modifiers: Optional[List[str]] = None,
        physical_status: Optional[str] = None,
        additional_modifying_units: int = 0,
    ) -> Tuple[float, dict]:
        """
        Calculate Medicare allowed amount for an anesthesia service.

        Args:
            procedure_code: CPT anesthesia code (00xxx-01xxx)
            contractor: Medicare contractor code
            locality: Medicare locality code
            time_minutes: Total anesthesia time in minutes
            modifiers: Optional list of procedure modifiers
            physical_status: Physical status modifier (P1-P6)
            additional_modifying_units: Additional modifying units (e.g., qualifying circumstances)

        Returns:
            Tuple of (allowed_amount, calculation_details)

        Raises:
            ValueError: If procedure code or locality not found
        """
        # Get base unit data
        base_unit_data = self.fee_schedule.get_anesthesia_base_unit(procedure_code)
        if not base_unit_data:
            raise ValueError(
                f"Anesthesia procedure code {procedure_code} not found in base unit crosswalk. "
                f"This may not be a valid anesthesia code or the code is not in the database."
            )

        # Get conversion factor for locality
        anes_data = self.fee_schedule.get_anesthesia(contractor, locality)
        if not anes_data:
            raise ValueError(
                f"Anesthesia conversion factor not found for contractor {contractor}, "
                f"locality {locality}"
            )

        # Calculate time units (15-minute increments, rounded up)
        time_units = math.ceil(time_minutes / 15.0)

        # Calculate modifying units from various sources
        modifying_units = additional_modifying_units

        # Add physical status modifying units
        if physical_status:
            ps_units, ps_note = self._get_physical_status_units(physical_status)
            modifying_units += ps_units
        else:
            ps_note = None

        # Process anesthesia-specific modifiers
        modifier_units, modifier_notes = self._process_anesthesia_modifiers(modifiers)
        modifying_units += modifier_units

        # Calculate total units
        total_units = base_unit_data.base_units + time_units + modifying_units

        # Calculate payment
        allowed_amount = total_units * anes_data.conversion_factor

        # Build calculation details
        details = {
            "procedure_code": procedure_code,
            "description": base_unit_data.description,
            "contractor": contractor,
            "locality": locality,
            "locality_name": anes_data.locality_name,
            "base_units": base_unit_data.base_units,
            "time_minutes": time_minutes,
            "time_units": time_units,
            "modifying_units": modifying_units,
            "total_units": total_units,
            "conversion_factor": anes_data.conversion_factor,
            "allowed_amount": allowed_amount,
            "notes": []
        }

        # Add notes
        if ps_note:
            details["notes"].append(ps_note)
        if modifier_notes:
            details["notes"].extend(modifier_notes)
        if additional_modifying_units > 0:
            details["notes"].append(f"Additional modifying units: {additional_modifying_units}")

        return allowed_amount, details

    def _get_physical_status_units(self, physical_status: str) -> Tuple[int, Optional[str]]:
        """
        Get modifying units for physical status.

        Physical Status Modifiers:
        - P1: Normal healthy patient (0 units)
        - P2: Patient with mild systemic disease (0 units)
        - P3: Patient with severe systemic disease (1 unit)
        - P4: Patient with severe systemic disease that is a constant threat to life (2 units)
        - P5: Moribund patient not expected to survive without operation (3 units)
        - P6: Declared brain-dead patient whose organs are being removed for donor purposes (0 units)

        Args:
            physical_status: Physical status modifier (P1-P6)

        Returns:
            Tuple of (modifying_units, note)
        """
        ps = physical_status.upper()

        physical_status_map = {
            "P1": (0, "P1: Normal healthy patient"),
            "P2": (0, "P2: Patient with mild systemic disease"),
            "P3": (1, "P3: Patient with severe systemic disease (+1 unit)"),
            "P4": (2, "P4: Patient with life-threatening systemic disease (+2 units)"),
            "P5": (3, "P5: Moribund patient (+3 units)"),
            "P6": (0, "P6: Brain-dead organ donor")
        }

        if ps in physical_status_map:
            return physical_status_map[ps]

        return 0, f"Unknown physical status: {physical_status}"

    def _process_anesthesia_modifiers(
        self,
        modifiers: Optional[List[str]]
    ) -> Tuple[int, List[str]]:
        """
        Process anesthesia-specific modifiers.

        Common anesthesia modifiers:
        - QK: Medical direction of 2-4 concurrent anesthesia services
        - QX: CRNA service with medical direction by a physician
        - QY: Medical direction of one CRNA by an anesthesiologist
        - QZ: CRNA service without medical direction
        - AA: Anesthesia services performed personally by anesthesiologist
        - AD: Medical supervision by a physician: more than 4 concurrent anesthesia procedures
        - QS: Monitored anesthesia care service
        - 23: Unusual anesthesia (for procedures normally not requiring anesthesia)
        - 47: Anesthesia by surgeon (not typically paid)

        Qualifying Circumstances (add units):
        - 99100: Anesthesia for patient of extreme age (under 1 year or over 70) (+1 unit)
        - 99116: Anesthesia complicated by utilization of total body hypothermia (+5 units)
        - 99135: Anesthesia complicated by utilization of controlled hypotension (+5 units)
        - 99140: Anesthesia complicated by emergency conditions (+2 units)

        Args:
            modifiers: List of procedure modifiers

        Returns:
            Tuple of (additional_units, notes_list)
        """
        additional_units = 0
        notes = []

        if not modifiers:
            return additional_units, notes

        for modifier in modifiers:
            if not modifier:
                continue

            modifier = modifier.upper()

            # Qualifying circumstances that add units
            if modifier == "99100":
                additional_units += 1
                notes.append("Qualifying circumstance: Extreme age (+1 unit)")
            elif modifier == "99116":
                additional_units += 5
                notes.append("Qualifying circumstance: Total body hypothermia (+5 units)")
            elif modifier == "99135":
                additional_units += 5
                notes.append("Qualifying circumstance: Controlled hypotension (+5 units)")
            elif modifier == "99140":
                additional_units += 2
                notes.append("Qualifying circumstance: Emergency conditions (+2 units)")

            # Provider-specific modifiers (payment methodology, not unit additions)
            elif modifier == "AA":
                notes.append("Anesthesia services performed personally by anesthesiologist")
            elif modifier == "QK":
                notes.append("Medical direction of 2-4 concurrent cases")
            elif modifier == "QX":
                notes.append("CRNA service with medical direction")
            elif modifier == "QY":
                notes.append("Medical direction of one CRNA")
            elif modifier == "QZ":
                notes.append("CRNA service without medical direction")
            elif modifier == "AD":
                notes.append("Medical supervision of >4 concurrent procedures")
            elif modifier == "QS":
                notes.append("Monitored anesthesia care service")
            elif modifier == "23":
                notes.append("Unusual anesthesia (procedure normally not requiring anesthesia)")
            elif modifier == "47":
                notes.append("Anesthesia by surgeon (typically not separately reimbursed)")

        return additional_units, notes
