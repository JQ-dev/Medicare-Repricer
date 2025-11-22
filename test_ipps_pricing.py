"""
Tests for Medicare IPPS (Inpatient Prospective Payment System) pricing functionality.

Run with: pytest test_ipps_pricing.py -v
"""

import pytest
from pathlib import Path
from medicare_repricing import MedicareRepricer, Claim, ClaimLine
from medicare_repricing.calculator import IPPSCalculator
from medicare_repricing.fee_schedule import MedicareFeeSchedule


class TestIPPSCalculator:
    """Test IPPS calculator functionality."""

    @pytest.fixture
    def fee_schedule(self):
        """Create a fee schedule with IPPS data loaded."""
        fee_schedule = MedicareFeeSchedule()
        data_dir = Path(__file__).parent / "data"
        fee_schedule.load_from_directory(data_dir)
        return fee_schedule

    @pytest.fixture
    def calculator(self, fee_schedule):
        """Create an IPPS calculator."""
        return IPPSCalculator(fee_schedule)

    def test_basic_drg_payment(self, calculator):
        """Test basic DRG payment calculation without adjustments."""
        # MS-DRG 470: Major Joint Replacement
        # Relative Weight: 1.7845
        # Hospital: 300001 (Scottsdale Surgical - non-teaching, non-DSH)
        # Wage Index: 1.0123
        # Expected: Base operating + capital payment

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="300001"
        )

        assert details["ms_drg"] == "470"
        assert details["drg_relative_weight"] == 1.7845
        assert details["hospital_name"] == "Scottsdale Surgical Hospital"
        assert details["wage_index"] == 1.0123
        assert details["ime_adjustment"] == 0.0  # Not a teaching hospital
        assert details["dsh_adjustment"] == 0.0  # Not a DSH hospital
        assert details["outlier_payment"] == 0.0  # No charges provided
        assert allowed_amount > 0
        # Base payment should be around $12,000-$13,000 for this DRG
        assert 11000 < allowed_amount < 14000

    def test_teaching_hospital_ime_adjustment(self, calculator):
        """Test IME adjustment for teaching hospitals."""
        # MS-DRG 470: Major Joint Replacement
        # Hospital: 100001 (Mass General - teaching hospital, IRB=0.85)
        # Should receive IME adjustment

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="100001"
        )

        assert details["is_teaching_hospital"] is True
        assert details["ime_adjustment"] > 0
        # IME should add roughly 10-15% to base payment for IRB=0.85
        # Formula: 1.34 × ((0.85 + 0.4)^0.405 - 1) ≈ 12.45%
        ime_percentage = details["ime_adjustment"] / details["base_drg_payment"]
        assert 0.10 < ime_percentage < 0.18

    def test_dsh_hospital_adjustment(self, calculator):
        """Test DSH adjustment for disproportionate share hospitals."""
        # MS-DRG 470
        # Hospital: 200001 (Atlanta Regional - DSH hospital, 28.3% DSH)
        # Should receive DSH adjustment

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="200001"
        )

        assert details["is_dsh_hospital"] is True
        assert details["dsh_adjustment"] > 0
        # DSH should add roughly 15-25% to base payment for DSH%=28.3
        dsh_percentage = details["dsh_adjustment"] / details["base_drg_payment"]
        assert 0.10 < dsh_percentage < 0.30

    def test_teaching_and_dsh_combined(self, calculator):
        """Test combined IME and DSH adjustments."""
        # MS-DRG 871: Septicemia (complex case)
        # Hospital: 100002 (Johns Hopkins - teaching + DSH)
        # Should receive both IME and DSH adjustments

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="871",
            provider_number="100002"
        )

        assert details["is_teaching_hospital"] is True
        assert details["is_dsh_hospital"] is True
        assert details["ime_adjustment"] > 0
        assert details["dsh_adjustment"] > 0
        # Total payment should be significantly higher than base (at least 25%)
        total_adjustments = details["ime_adjustment"] + details["dsh_adjustment"]
        assert total_adjustments > details["base_drg_payment"] * 0.25

    def test_outlier_payment(self, calculator):
        """Test outlier payment for high-cost cases."""
        # MS-DRG 470
        # Hospital: 300001
        # Provide very high charges to trigger outlier
        # Charges of $500,000 should trigger outlier payment

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="300001",
            total_charges=500000.0
        )

        assert details["outlier_payment"] > 0
        # Outlier should add significant amount for such high charges
        assert details["outlier_payment"] > 10000

    def test_no_outlier_for_normal_charges(self, calculator):
        """Test that normal charges don't trigger outlier."""
        # MS-DRG 470
        # Hospital: 300001
        # Normal charges around $50,000 should not trigger outlier

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="300001",
            total_charges=50000.0
        )

        assert details["outlier_payment"] == 0.0

    def test_high_wage_index_area(self, calculator):
        """Test payment in high wage index area."""
        # San Francisco area has very high wage index
        # Hospital: 100006 (UCSF - wage index 1.5234)
        # MS-DRG 470

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="100006"
        )

        assert details["wage_index"] == 1.5234
        # Higher wage index should result in higher operating payment
        assert details["operating_payment"] > 8000

    def test_low_wage_index_area(self, calculator):
        """Test payment in low wage index (rural) area."""
        # Rural Mississippi has low wage index
        # Hospital: 400002 (Mississippi Delta - wage index 0.7123)
        # MS-DRG 470

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="400002"
        )

        assert details["wage_index"] == 0.7123
        assert details["is_rural"] is True
        # Lower wage index should result in lower operating payment
        # But DSH should help offset (DSH%=38.2)
        assert details["dsh_adjustment"] > 0

    def test_high_complexity_drg(self, calculator):
        """Test high-complexity, high-weight DRG."""
        # MS-DRG 001: Heart Transplant (weight 26.1234)
        # Hospital: 100001 (Mass General)

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="001",
            provider_number="100001"
        )

        assert details["drg_relative_weight"] == 26.1234
        # Payment should be very high for heart transplant
        assert allowed_amount > 150000

    def test_low_complexity_drg(self, calculator):
        """Test low-complexity, low-weight DRG."""
        # MS-DRG 776: Vaginal delivery without complications (weight 0.5987)
        # Hospital: 300001

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="776",
            provider_number="300001"
        )

        assert details["drg_relative_weight"] == 0.5987
        # Payment should be relatively low
        assert 3500 < allowed_amount < 5500

    def test_operating_payment_calculation(self, calculator):
        """Test operating payment formula components."""
        # MS-DRG 470, Hospital 100001 (wage index 1.2543)

        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="100001"
        )

        # Operating payment should be present
        assert details["operating_payment"] > 0
        # Capital payment should be present
        assert details["capital_payment"] > 0
        # Base payment should equal operating + capital
        assert details["base_drg_payment"] == pytest.approx(
            details["operating_payment"] + details["capital_payment"],
            rel=0.01
        )

    def test_invalid_drg_code(self, calculator):
        """Test that invalid DRG code raises error."""
        with pytest.raises(ValueError, match="MS-DRG.*not found"):
            calculator.calculate_allowed_amount(
                ms_drg="99999",
                provider_number="100001"
            )

    def test_invalid_provider_number(self, calculator):
        """Test that invalid provider number raises error."""
        with pytest.raises(ValueError, match="Hospital.*not found"):
            calculator.calculate_allowed_amount(
                ms_drg="470",
                provider_number="999999"
            )

    def test_covered_days_tracking(self, calculator):
        """Test that covered days are tracked in details."""
        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="100001",
            covered_days=3
        )

        assert details["covered_days"] == 3
        assert details["geometric_mean_los"] == 2.1  # From MS-DRG data

    def test_notes_generation(self, calculator):
        """Test that appropriate notes are generated."""
        # Teaching + DSH + Outlier + Rural
        allowed_amount, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number="400002",  # Rural DSH hospital
            total_charges=500000.0
        )

        assert len(details["notes"]) > 0
        notes_text = " ".join(details["notes"])
        assert "DSH adjustment applied" in notes_text
        assert "Outlier payment applied" in notes_text
        assert "Rural hospital" in notes_text


class TestIPPSIntegration:
    """Test IPPS integration with MedicareRepricer."""

    @pytest.fixture
    def repricer(self):
        """Create a repricer with IPPS data loaded."""
        data_dir = Path(__file__).parent / "data"
        return MedicareRepricer(data_directory=data_dir)

    def test_inpatient_claim_routing(self, repricer):
        """Test that inpatient claims are routed to IPPS calculator."""
        claim = Claim(
            claim_id="IPPS-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",  # Placeholder
                    place_of_service="21",  # Inpatient
                    locality="01",
                    units=1,
                    ms_drg_code="470",
                    provider_number="100001"
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert len(repriced.lines) == 1
        assert repriced.lines[0].service_type == "IPPS"
        assert repriced.lines[0].ms_drg_code == "470"
        assert repriced.lines[0].hospital_name == "Massachusetts General Hospital"
        assert repriced.total_allowed > 0

    def test_mixed_claim_types(self, repricer):
        """Test claim with both inpatient and outpatient services."""
        claim = Claim(
            claim_id="MIXED-001",
            lines=[
                # Inpatient stay
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="470",
                    provider_number="100001"
                ),
                # Outpatient office visit (shouldn't happen in reality, but test routing)
                ClaimLine(
                    line_number=2,
                    procedure_code="99213",
                    place_of_service="11",
                    locality="01",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert len(repriced.lines) == 2
        assert repriced.lines[0].service_type == "IPPS"
        assert repriced.lines[1].service_type == "PFS"

    def test_ipps_with_outlier(self, repricer):
        """Test IPPS claim with outlier charges."""
        claim = Claim(
            claim_id="IPPS-OUTLIER-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="001",  # Heart transplant
                    provider_number="100001",
                    total_charges=1500000.0,  # Very high charges
                    covered_days=30
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.lines[0].outlier_payment > 0
        assert repriced.lines[0].covered_days == 30

    def test_teaching_hospital_details(self, repricer):
        """Test that teaching hospital details are captured."""
        claim = Claim(
            claim_id="IPPS-TEACH-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="871",
                    provider_number="100007"  # NewYork-Presbyterian
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)
        line = repriced.lines[0]

        assert line.ime_adjustment > 0
        assert "IME adjustment applied" in line.adjustment_reason

    def test_rural_hospital(self, repricer):
        """Test rural hospital designation and adjustments."""
        claim = Claim(
            claim_id="IPPS-RURAL-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="470",
                    provider_number="400001"  # Rural Kansas hospital
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)
        line = repriced.lines[0]

        assert "Rural hospital" in line.adjustment_reason
        assert line.dsh_adjustment > 0

    def test_ipps_error_handling(self, repricer):
        """Test error handling for invalid IPPS claims."""
        claim = Claim(
            claim_id="IPPS-ERROR-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="99999",  # Invalid DRG
                    provider_number="100001"
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.lines[0].medicare_allowed == 0.0
        assert "ERROR" in repriced.lines[0].adjustment_reason

    def test_comprehensive_ipps_claim(self, repricer):
        """Test a comprehensive IPPS claim with all features."""
        claim = Claim(
            claim_id="IPPS-COMPREHENSIVE-001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",
                    place_of_service="21",
                    locality="01",
                    units=1,
                    ms_drg_code="001",  # Heart transplant
                    provider_number="100007",  # NYC Presbyterian (teaching + DSH)
                    total_charges=2000000.0,
                    covered_days=37
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)
        line = repriced.lines[0]

        # Verify all components are present
        assert line.service_type == "IPPS"
        assert line.drg_relative_weight > 20  # Very high weight
        assert line.base_drg_payment > 0
        assert line.operating_payment > 0
        assert line.capital_payment > 0
        assert line.ime_adjustment > 0  # Teaching hospital
        assert line.dsh_adjustment > 0  # DSH hospital
        assert line.outlier_payment > 0  # High charges
        assert line.medicare_allowed > 200000  # Should be very high
        assert line.covered_days == 37
        assert line.geometric_mean_los > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
