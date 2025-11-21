"""
Tests for Medicare anesthesia pricing functionality.

Run with: pytest test_anesthesia_pricing.py -v
"""

import pytest
from pathlib import Path
from medicare_repricing import MedicareRepricer, Claim, ClaimLine
from medicare_repricing.calculator import AnesthesiaCalculator
from medicare_repricing.fee_schedule import MedicareFeeSchedule


class TestAnesthesiaCalculator:
    """Test anesthesia calculator functionality."""

    @pytest.fixture
    def fee_schedule(self):
        """Create a fee schedule with anesthesia data loaded."""
        fee_schedule = MedicareFeeSchedule()
        data_dir = Path(__file__).parent / "data"
        fee_schedule.load_from_directory(data_dir)
        return fee_schedule

    @pytest.fixture
    def calculator(self, fee_schedule):
        """Create an anesthesia calculator."""
        return AnesthesiaCalculator(fee_schedule)

    def test_basic_anesthesia_calculation(self, calculator):
        """Test basic anesthesia payment calculation."""
        # Code 00100: Anesth salivary gland (5 base units)
        # 90 minutes = 6 time units (90/15 = 6)
        # Alabama locality: CF = $19.31
        # Expected: (5 + 6) × 19.31 = $212.41

        allowed_amount, details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status=None,
            additional_modifying_units=0
        )

        assert details["base_units"] == 5
        assert details["time_units"] == 6
        assert details["modifying_units"] == 0
        assert details["total_units"] == 11
        assert details["conversion_factor"] == 19.31
        assert allowed_amount == pytest.approx(212.41, rel=0.01)

    def test_time_unit_rounding(self, calculator):
        """Test that time units are calculated correctly with rounding up."""
        # Test various time values
        test_cases = [
            (15, 1),   # Exactly 15 minutes = 1 unit
            (16, 2),   # 16 minutes rounds up to 2 units
            (30, 2),   # 30 minutes = 2 units
            (31, 3),   # 31 minutes rounds up to 3 units
            (45, 3),   # 45 minutes = 3 units
            (60, 4),   # 60 minutes = 4 units
            (90, 6),   # 90 minutes = 6 units
            (91, 7),   # 91 minutes rounds up to 7 units
        ]

        for time_minutes, expected_units in test_cases:
            _, details = calculator.calculate_allowed_amount(
                procedure_code="00100",
                contractor="10112",
                locality="00",
                time_minutes=time_minutes,
                modifiers=None,
                physical_status=None,
                additional_modifying_units=0
            )
            assert details["time_units"] == expected_units, \
                f"Failed for {time_minutes} minutes: expected {expected_units}, got {details['time_units']}"

    def test_physical_status_modifiers(self, calculator):
        """Test physical status modifier units."""
        # P1 and P2 add 0 units
        # P3 adds 1 unit
        # P4 adds 2 units
        # P5 adds 3 units

        # Base: (5 + 6) = 11 units
        base_amount, _ = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status="P1",
            additional_modifying_units=0
        )

        # P3: (5 + 6 + 1) = 12 units
        p3_amount, p3_details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status="P3",
            additional_modifying_units=0
        )

        assert p3_details["modifying_units"] == 1
        assert p3_amount > base_amount
        assert p3_amount == pytest.approx(base_amount + 19.31, rel=0.01)

        # P5: (5 + 6 + 3) = 14 units
        p5_amount, p5_details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status="P5",
            additional_modifying_units=0
        )

        assert p5_details["modifying_units"] == 3
        assert p5_amount == pytest.approx(base_amount + (3 * 19.31), rel=0.01)

    def test_qualifying_circumstance_modifiers(self, calculator):
        """Test qualifying circumstance modifiers that add units."""
        # 99100: Extreme age (+1 unit)
        # 99140: Emergency conditions (+2 units)
        # 99116: Total body hypothermia (+5 units)
        # 99135: Controlled hypotension (+5 units)

        # Base: (5 + 6) = 11 units
        base_amount, _ = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status=None,
            additional_modifying_units=0
        )

        # With 99140 emergency modifier: (5 + 6 + 2) = 13 units
        emergency_amount, emergency_details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=["99140"],
            physical_status=None,
            additional_modifying_units=0
        )

        assert emergency_details["modifying_units"] == 2
        assert emergency_amount == pytest.approx(base_amount + (2 * 19.31), rel=0.01)

    def test_complex_case_with_multiple_modifiers(self, calculator):
        """Test complex anesthesia case with physical status and qualifying circumstances."""
        # Code 00562: Heart surgery with pump (25 base units)
        # 180 minutes = 12 time units
        # P4 physical status = +2 units
        # 99140 emergency = +2 units
        # Total: 25 + 12 + 2 + 2 = 41 units
        # Los Angeles CF: $21.22
        # Expected: 41 × 21.22 = $870.02

        allowed_amount, details = calculator.calculate_allowed_amount(
            procedure_code="00562",
            contractor="01182",
            locality="18",
            time_minutes=180,
            modifiers=["99140", "AA"],  # Emergency + anesthesiologist
            physical_status="P4",
            additional_modifying_units=0
        )

        assert details["base_units"] == 25
        assert details["time_units"] == 12
        assert details["modifying_units"] == 4  # 2 from P4, 2 from 99140
        assert details["total_units"] == 41
        assert details["conversion_factor"] == 21.22
        assert allowed_amount == pytest.approx(870.02, rel=0.01)

    def test_locality_variation(self, calculator):
        """Test that conversion factors vary by locality."""
        # Same procedure, same time, different localities

        # Alabama (lowest): $19.31
        alabama_amount, alabama_details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="10112",
            locality="00",
            time_minutes=90,
            modifiers=None,
            physical_status=None,
            additional_modifying_units=0
        )

        # Alaska (highest): $27.86
        alaska_amount, alaska_details = calculator.calculate_allowed_amount(
            procedure_code="00100",
            contractor="02102",
            locality="01",
            time_minutes=90,
            modifiers=None,
            physical_status=None,
            additional_modifying_units=0
        )

        assert alabama_details["conversion_factor"] == 19.31
        assert alaska_details["conversion_factor"] == 27.86
        assert alaska_amount > alabama_amount
        assert alaska_amount == pytest.approx(alabama_amount * (27.86 / 19.31), rel=0.01)

    def test_invalid_procedure_code(self, calculator):
        """Test error handling for invalid anesthesia code."""
        with pytest.raises(ValueError, match="not found in base unit crosswalk"):
            calculator.calculate_allowed_amount(
                procedure_code="99999",
                contractor="10112",
                locality="00",
                time_minutes=90,
                modifiers=None,
                physical_status=None,
                additional_modifying_units=0
            )

    def test_invalid_locality(self, calculator):
        """Test error handling for invalid locality."""
        with pytest.raises(ValueError, match="conversion factor not found"):
            calculator.calculate_allowed_amount(
                procedure_code="00100",
                contractor="99999",
                locality="99",
                time_minutes=90,
                modifiers=None,
                physical_status=None,
                additional_modifying_units=0
            )


class TestAnesthesiaIntegration:
    """Test anesthesia pricing integration with MedicareRepricer."""

    @pytest.fixture
    def repricer(self):
        """Create a repricer with full data loaded."""
        data_dir = Path(__file__).parent / "data"
        return MedicareRepricer(data_directory=data_dir)

    def test_simple_anesthesia_claim(self, repricer):
        """Test repricing a simple anesthesia claim."""
        claim = Claim(
            claim_id="ANES001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",
                    modifiers=None,
                    place_of_service="22",  # Outpatient hospital
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=90,
                    physical_status_modifier=None,
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.claim_id == "ANES001"
        assert len(repriced.lines) == 1
        assert repriced.lines[0].service_type == "ANESTHESIA"
        assert repriced.lines[0].anesthesia_base_units == 5
        assert repriced.lines[0].anesthesia_time_units == 6
        assert repriced.lines[0].anesthesia_total_units == 11
        assert repriced.total_allowed > 0

    def test_anesthesia_with_physical_status(self, repricer):
        """Test anesthesia claim with physical status modifier."""
        claim = Claim(
            claim_id="ANES002",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00562",  # Heart surgery with pump
                    modifiers=["AA"],
                    place_of_service="22",
                    locality="18",  # Los Angeles
                    units=1,
                    anesthesia_time_minutes=180,
                    physical_status_modifier="P4",
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.lines[0].service_type == "ANESTHESIA"
        assert repriced.lines[0].anesthesia_base_units == 25
        assert repriced.lines[0].anesthesia_time_units == 12
        assert repriced.lines[0].anesthesia_modifying_units == 2  # P4 adds 2 units
        assert repriced.lines[0].anesthesia_total_units == 39

    def test_anesthesia_with_qualifying_circumstances(self, repricer):
        """Test anesthesia with qualifying circumstance modifiers."""
        claim = Claim(
            claim_id="ANES003",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",
                    modifiers=["99100", "AA"],  # Extreme age + anesthesiologist
                    place_of_service="22",
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=60,
                    physical_status_modifier=None,
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.lines[0].anesthesia_modifying_units == 1  # 99100 adds 1 unit
        assert repriced.lines[0].anesthesia_total_units == 10  # 5 base + 4 time + 1 modifier

    def test_mixed_claim_anesthesia_and_regular(self, repricer):
        """Test claim with both anesthesia and regular procedure codes."""
        claim = Claim(
            claim_id="MIXED001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",  # Anesthesia
                    modifiers=None,
                    place_of_service="22",
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=90,
                    physical_status_modifier=None,
                    anesthesia_modifying_units=None
                ),
                ClaimLine(
                    line_number=2,
                    procedure_code="99213",  # Office visit (regular PFS)
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert len(repriced.lines) == 2
        assert repriced.lines[0].service_type == "ANESTHESIA"
        assert repriced.lines[1].service_type == "PFS"
        assert repriced.lines[0].anesthesia_base_units is not None
        assert repriced.lines[1].work_rvu is not None

    def test_anesthesia_multiple_units(self, repricer):
        """Test that units multiplier applies to anesthesia."""
        # Single unit
        claim_single = Claim(
            claim_id="ANES_UNIT1",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",
                    modifiers=None,
                    place_of_service="22",
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=90,
                    physical_status_modifier=None,
                    anesthesia_modifying_units=None
                )
            ]
        )

        # Two units
        claim_double = Claim(
            claim_id="ANES_UNIT2",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",
                    modifiers=None,
                    place_of_service="22",
                    locality="00",
                    units=2,
                    anesthesia_time_minutes=90,
                    physical_status_modifier=None,
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced_single = repricer.reprice_claim(claim_single)
        repriced_double = repricer.reprice_claim(claim_double)

        single_amount = repriced_single.lines[0].medicare_allowed
        double_amount = repriced_double.lines[0].medicare_allowed

        assert double_amount == pytest.approx(single_amount * 2, rel=0.01)

    def test_anesthesia_missing_time(self, repricer):
        """Test error handling when anesthesia time is missing."""
        claim = Claim(
            claim_id="ANES_ERROR",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00100",
                    modifiers=None,
                    place_of_service="22",
                    locality="00",
                    units=1,
                    # Missing anesthesia_time_minutes
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        # Should handle error gracefully
        assert repriced.lines[0].medicare_allowed == 0.0
        assert "ERROR" in repriced.lines[0].adjustment_reason
        assert "time in minutes is required" in repriced.lines[0].adjustment_reason


class TestAnesthesiaCodeDetection:
    """Test anesthesia code detection logic."""

    @pytest.fixture
    def repricer(self):
        """Create a basic repricer."""
        data_dir = Path(__file__).parent / "data"
        return MedicareRepricer(data_directory=data_dir)

    def test_anesthesia_code_detection(self, repricer):
        """Test that anesthesia codes are correctly detected."""
        # Valid anesthesia codes
        assert repricer._is_anesthesia_code("00100") is True
        assert repricer._is_anesthesia_code("00562") is True
        assert repricer._is_anesthesia_code("01382") is True
        assert repricer._is_anesthesia_code("01999") is True

        # Non-anesthesia codes
        assert repricer._is_anesthesia_code("99213") is False
        assert repricer._is_anesthesia_code("80053") is False
        assert repricer._is_anesthesia_code("12001") is False

        # Edge cases
        assert repricer._is_anesthesia_code("0010") is False  # Too short
        assert repricer._is_anesthesia_code("001000") is False  # Too long
        assert repricer._is_anesthesia_code("02000") is False  # Starts with 02


class TestAnesthesiaRealWorldScenarios:
    """Test real-world anesthesia scenarios."""

    @pytest.fixture
    def repricer(self):
        """Create a repricer with full data loaded."""
        data_dir = Path(__file__).parent / "data"
        return MedicareRepricer(data_directory=data_dir)

    def test_cabg_surgery_anesthesia(self, repricer):
        """Test CABG surgery anesthesia (complex cardiac case)."""
        # 00562: Anesthesia for heart surgery with pump
        # 240 minutes (4 hours)
        # P3 physical status (severe systemic disease)
        # Los Angeles locality

        claim = Claim(
            claim_id="CABG001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00562",
                    modifiers=["AA"],  # Anesthesiologist
                    place_of_service="22",
                    locality="18",
                    units=1,
                    anesthesia_time_minutes=240,
                    physical_status_modifier="P3",
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        line = repriced.lines[0]
        assert line.service_type == "ANESTHESIA"
        assert line.anesthesia_base_units == 25
        assert line.anesthesia_time_units == 16  # 240/15 = 16
        assert line.anesthesia_modifying_units == 1  # P3 adds 1
        assert line.anesthesia_total_units == 42  # 25 + 16 + 1
        assert line.conversion_factor == 21.22
        assert line.medicare_allowed == pytest.approx(891.24, rel=0.01)

    def test_hip_replacement_anesthesia(self, repricer):
        """Test hip replacement anesthesia (routine orthopedic case)."""
        # 01200: Anesthesia for hip replacement
        # 120 minutes (2 hours)
        # P2 physical status (mild systemic disease)

        claim = Claim(
            claim_id="HIP001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="01200",
                    modifiers=["AA"],
                    place_of_service="22",
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=120,
                    physical_status_modifier="P2",
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        line = repriced.lines[0]
        assert line.anesthesia_base_units == 8
        assert line.anesthesia_time_units == 8  # 120/15 = 8
        assert line.anesthesia_modifying_units == 0  # P2 adds 0
        assert line.anesthesia_total_units == 16
        assert line.medicare_allowed > 0

    def test_pediatric_emergency_anesthesia(self, repricer):
        """Test pediatric emergency case with multiple modifying circumstances."""
        # 00326: Anesthesia for larynx/trach < 1 yr (pediatric)
        # 45 minutes
        # P4 physical status (life-threatening)
        # 99100: Extreme age
        # 99140: Emergency conditions

        claim = Claim(
            claim_id="PED_EMERG001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="00326",
                    modifiers=["99100", "99140"],  # Age + emergency
                    place_of_service="23",  # Emergency room
                    locality="00",
                    units=1,
                    anesthesia_time_minutes=45,
                    physical_status_modifier="P4",
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        line = repriced.lines[0]
        assert line.anesthesia_base_units == 8
        assert line.anesthesia_time_units == 3  # 45/15 = 3
        # Modifying: P4 (2) + 99100 (1) + 99140 (2) = 5 units
        assert line.anesthesia_modifying_units == 5
        assert line.anesthesia_total_units == 16  # 8 + 3 + 5
        assert line.medicare_allowed > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
