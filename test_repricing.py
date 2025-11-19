"""
Tests for Medicare repricing functionality.

Run with: pytest test_repricing.py -v
"""

import pytest
from medicare_repricing import MedicareRepricer, Claim, ClaimLine


class TestBasicRepricing:
    """Test basic repricing functionality."""

    def test_simple_office_visit(self):
        """Test repricing a simple office visit."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="TEST001",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert repriced.claim_id == "TEST001"
        assert len(repriced.lines) == 1
        assert repriced.total_allowed > 0
        assert repriced.lines[0].medicare_allowed > 0

    def test_multiple_lines(self):
        """Test claim with multiple lines."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="TEST002",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                ),
                ClaimLine(
                    line_number=2,
                    procedure_code="80053",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        assert len(repriced.lines) == 2
        assert repriced.total_allowed == sum(line.medicare_allowed for line in repriced.lines)

    def test_units_multiplier(self):
        """Test that units correctly multiply the allowed amount."""
        repricer = MedicareRepricer()

        # Single unit
        claim_single = Claim(
            claim_id="TEST003A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        # Three units
        claim_triple = Claim(
            claim_id="TEST003B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=3
                )
            ]
        )

        repriced_single = repricer.reprice_claim(claim_single)
        repriced_triple = repricer.reprice_claim(claim_triple)

        assert abs(repriced_triple.total_allowed - (repriced_single.total_allowed * 3)) < 0.01


class TestGeographicAdjustment:
    """Test geographic GPCI adjustments."""

    def test_different_localities(self):
        """Test that different localities produce different allowed amounts."""
        repricer = MedicareRepricer()

        # National average
        claim_national = Claim(
            claim_id="TEST004A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",  # National average
                    units=1
                )
            ]
        )

        # Manhattan (higher cost)
        claim_manhattan = Claim(
            claim_id="TEST004B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="01",  # Manhattan
                    units=1
                )
            ]
        )

        repriced_national = repricer.reprice_claim(claim_national)
        repriced_manhattan = repricer.reprice_claim(claim_manhattan)

        # Manhattan should have higher allowed amount due to GPCI
        assert repriced_manhattan.total_allowed > repriced_national.total_allowed


class TestFacilityVsNonFacility:
    """Test facility vs non-facility pricing."""

    def test_office_vs_hospital(self):
        """Test that office visits pay more than hospital outpatient due to PE."""
        repricer = MedicareRepricer()

        # Office (non-facility)
        claim_office = Claim(
            claim_id="TEST005A",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",  # Office
                    locality="00",
                    units=1
                )
            ]
        )

        # Hospital outpatient (facility)
        claim_hospital = Claim(
            claim_id="TEST005B",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="22",  # Outpatient hospital
                    locality="00",
                    units=1
                )
            ]
        )

        repriced_office = repricer.reprice_claim(claim_office)
        repriced_hospital = repricer.reprice_claim(claim_hospital)

        # Office should pay more due to higher PE RVU
        assert repriced_office.total_allowed > repriced_hospital.total_allowed


class TestModifiers:
    """Test modifier handling."""

    def test_modifier_26_professional_component(self):
        """Test that modifier 26 reduces payment (professional component only)."""
        repricer = MedicareRepricer()

        # Global
        claim_global = Claim(
            claim_id="TEST006A",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="71046",
                    modifiers=None,
                    place_of_service="22",
                    locality="00",
                    units=1
                )
            ]
        )

        # Professional component only
        claim_prof = Claim(
            claim_id="TEST006B",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="71046",
                    modifiers=["26"],
                    place_of_service="22",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced_global = repricer.reprice_claim(claim_global)
        repriced_prof = repricer.reprice_claim(claim_prof)

        # Professional component should be less than global
        assert repriced_prof.total_allowed < repriced_global.total_allowed
        # PE RVU should be zero for modifier 26
        assert repriced_prof.lines[0].pe_rvu == 0.0

    def test_modifier_50_bilateral(self):
        """Test that modifier 50 increases payment by 150%."""
        repricer = MedicareRepricer()

        # Single procedure
        claim_single = Claim(
            claim_id="TEST007A",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="20610",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        # Bilateral procedure
        claim_bilateral = Claim(
            claim_id="TEST007B",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="20610",
                    modifiers=["50"],
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced_single = repricer.reprice_claim(claim_single)
        repriced_bilateral = repricer.reprice_claim(claim_bilateral)

        # Bilateral should be 150% of single
        expected = repriced_single.total_allowed * 1.5
        assert abs(repriced_bilateral.total_allowed - expected) < 0.01


class TestMPPR:
    """Test Multiple Procedure Payment Reduction."""

    def test_mppr_application(self):
        """Test that MPPR reduces payment for second procedure."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="TEST008",            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="12002",  # Higher RVU - should be first
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                ),
                ClaimLine(
                    line_number=2,
                    procedure_code="12001",  # Lower RVU - should be second with MPPR
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        # Should have MPPR note
        assert "MPPR" in " ".join(repriced.notes)


class TestValidation:
    """Test claim validation."""

    def test_missing_claim_id(self):
        """Test that missing claim ID raises error during repricing."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99213",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        with pytest.raises(ValueError, match="Claim ID"):
            repricer.reprice_claim(claim)

    def test_invalid_procedure_code(self):
        """Test handling of unknown procedure code."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="TEST011",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99999",  # Unknown code
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        # Should handle gracefully with error in adjustment_reason
        assert "ERROR" in repriced.lines[0].adjustment_reason
        assert repriced.lines[0].medicare_allowed == 0.0


class TestFeeScheduleQuery:
    """Test fee schedule querying."""

    def test_get_procedure_info(self):
        """Test querying procedure information."""
        repricer = MedicareRepricer()

        info = repricer.get_procedure_info("99213")

        assert info is not None
        assert info["procedure_code"] == "99213"
        assert "description" in info
        assert info["work_rvu_non_facility"] > 0

    def test_get_locality_info(self):
        """Test querying locality information."""
        repricer = MedicareRepricer()

        info = repricer.get_locality_info("01")

        assert info is not None
        assert info["locality"] == "01"
        assert "locality_name" in info
        assert info["work_gpci"] > 0

    def test_unknown_procedure(self):
        """Test querying unknown procedure."""
        repricer = MedicareRepricer()

        info = repricer.get_procedure_info("99999")

        assert info is None


class TestMultipleModifiers:
    """Test multiple modifier handling."""

    def test_two_modifiers(self):
        """Test that two modifiers can be applied to a single procedure."""
        repricer = MedicareRepricer()

        # Single modifier
        claim_single_mod = Claim(
            claim_id="TEST012A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=["50"],
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        # Two modifiers
        claim_two_mods = Claim(
            claim_id="TEST012B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=["50", "59"],
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced_single = repricer.reprice_claim(claim_single_mod)
        repriced_two = repricer.reprice_claim(claim_two_mods)

        # Both should have modifiers applied
        assert repriced_single.lines[0].modifiers == ["50"]
        assert repriced_two.lines[0].modifiers == ["50", "59"]
        # Both should have adjustment notes
        assert repriced_single.lines[0].adjustment_reason is not None
        assert repriced_two.lines[0].adjustment_reason is not None

    def test_modifier_order_sequential(self):
        """Test that modifiers are applied sequentially."""
        repricer = MedicareRepricer()

        # No modifiers
        claim_none = Claim(
            claim_id="TEST013A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        # Modifier 52 (50% reduction)
        claim_mod = Claim(
            claim_id="TEST013B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=["52"],
                    place_of_service="11",
                    locality="00",
                    units=1
                )
            ]
        )

        repriced_none = repricer.reprice_claim(claim_none)
        repriced_mod = repricer.reprice_claim(claim_mod)

        # Modifier 52 should reduce payment by 50%
        expected = repriced_none.total_allowed * 0.5
        assert abs(repriced_mod.total_allowed - expected) < 0.01


class TestZipCodeMapping:
    """Test zip code to locality mapping."""

    def test_zip_to_locality_mapping(self):
        """Test that zip codes are correctly mapped to localities."""
        repricer = MedicareRepricer()

        claim = Claim(
            claim_id="TEST014",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    zip_code="10001",  # Manhattan - should map to locality 01
                    units=1
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)

        # Check that locality was determined from zip code
        assert repriced.lines[0].locality == "01"
        assert repriced.lines[0].zip_code == "10001"

    def test_zip_vs_locality_same_result(self):
        """Test that using zip code or locality directly gives same result."""
        repricer = MedicareRepricer()

        # Using locality directly
        claim_locality = Claim(
            claim_id="TEST015A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    locality="01",
                    units=1
                )
            ]
        )

        # Using zip code that maps to same locality
        claim_zip = Claim(
            claim_id="TEST015B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    zip_code="10001",  # Maps to locality 01
                    units=1
                )
            ]
        )

        repriced_locality = repricer.reprice_claim(claim_locality)
        repriced_zip = repricer.reprice_claim(claim_zip)

        # Should produce same allowed amount
        assert abs(repriced_locality.total_allowed - repriced_zip.total_allowed) < 0.01

    def test_different_zip_codes_different_amounts(self):
        """Test that different zip codes produce different allowed amounts."""
        repricer = MedicareRepricer()

        # Manhattan (high cost)
        claim_manhattan = Claim(
            claim_id="TEST016A",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    zip_code="10001",  # Manhattan
                    units=1
                )
            ]
        )

        # National average
        claim_national = Claim(
            claim_id="TEST016B",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="99214",
                    modifiers=None,
                    place_of_service="11",
                    locality="00",  # National average
                    units=1
                )
            ]
        )

        repriced_manhattan = repricer.reprice_claim(claim_manhattan)
        repriced_national = repricer.reprice_claim(claim_national)

        # Manhattan should have different allowed amount
        assert repriced_manhattan.total_allowed != repriced_national.total_allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
