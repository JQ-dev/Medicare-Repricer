"""
Example usage of the Medicare Repricing Interface.

This script demonstrates how to use the Medicare repricing system
with various scenarios.
"""

from pathlib import Path
from medicare_repricing import MedicareRepricer, Claim, ClaimLine


def example_1_simple_office_visit():
    """Example 1: Simple office visit with lab work."""
    print("=" * 80)
    print("Example 1: Simple Office Visit with Lab Work")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99213",  # Office visit, established patient
                modifiers=None,
                place_of_service="11",  # Office
                locality="00",  # National average
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="80053",  # Comprehensive metabolic panel
                modifiers=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"\nLine Items:")
    print(f"{'Line':<6} {'Procedure':<12} {'Description':<40} {'Allowed':<12}")
    print("-" * 80)

    descriptions = {
        "99213": "Office visit, established patient, moderate",
        "80053": "Comprehensive metabolic panel"
    }

    for line in repriced.lines:
        desc = descriptions.get(line.procedure_code, "")
        print(f"{line.line_number:<6} {line.procedure_code:<12} {desc:<40} ${line.medicare_allowed:>10.2f}")

    print(f"\n{'Total Medicare Allowed:':<60} ${repriced.total_allowed:>10.2f}")
    print(f"\nNotes:")
    for note in repriced.notes:
        print(f"  - {note}")
    print()


def example_2_geographic_variation():
    """Example 2: Same services in different geographic locations."""
    print("=" * 80)
    print("Example 2: Geographic Variation (New York vs Texas)")
    print("=" * 80)

    repricer = MedicareRepricer()

    # New York (Manhattan) - High cost area
    claim_ny = Claim(
        claim_id="CLM002-NY",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",
                modifiers=None,
                place_of_service="11",
                locality="01",  # Manhattan, NY
                units=1
            ),
        ]
    )

    # Texas (Dallas) - Lower cost area
    claim_tx = Claim(
        claim_id="CLM002-TX",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",
                modifiers=None,
                place_of_service="11",
                locality="26",  # Dallas, TX
                units=1
            ),
        ]
    )

    repriced_ny = repricer.reprice_claim(claim_ny)
    repriced_tx = repricer.reprice_claim(claim_tx)

    print(f"\nProcedure: 99214 (Office visit, established patient, high complexity)")
    print(f"\nNew York (Manhattan):")
    print(f"  Work GPCI: {repriced_ny.lines[0].work_gpci:.3f}")
    print(f"  PE GPCI:   {repriced_ny.lines[0].pe_gpci:.3f}")
    print(f"  MP GPCI:   {repriced_ny.lines[0].mp_gpci:.3f}")
    print(f"  Allowed:   ${repriced_ny.total_allowed:.2f}")

    print(f"\nTexas (Dallas):")
    print(f"  Work GPCI: {repriced_tx.lines[0].work_gpci:.3f}")
    print(f"  PE GPCI:   {repriced_tx.lines[0].pe_gpci:.3f}")
    print(f"  MP GPCI:   {repriced_tx.lines[0].mp_gpci:.3f}")
    print(f"  Allowed:   ${repriced_tx.total_allowed:.2f}")

    difference = repriced_ny.total_allowed - repriced_tx.total_allowed
    print(f"\nDifference: ${difference:.2f} ({(difference/repriced_tx.total_allowed*100):.1f}% more in NY)")
    print()


def example_3_facility_vs_non_facility():
    """Example 3: Facility vs non-facility pricing."""
    print("=" * 80)
    print("Example 3: Facility vs Non-Facility Pricing")
    print("=" * 80)

    repricer = MedicareRepricer()

    # Non-facility (Office)
    claim_office = Claim(
        claim_id="CLM003-OFFICE",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99203",
                modifiers=None,
                place_of_service="11",  # Office
                locality="00",
                units=1
            ),
        ]
    )

    # Facility (Hospital Outpatient)
    claim_hospital = Claim(
        claim_id="CLM003-HOSPITAL",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99203",
                modifiers=None,
                place_of_service="22",  # Outpatient Hospital
                locality="00",
                units=1
            ),
        ]
    )

    repriced_office = repricer.reprice_claim(claim_office)
    repriced_hospital = repricer.reprice_claim(claim_hospital)

    print(f"\nProcedure: 99203 (Office visit, new patient, moderate)")
    print(f"\nNon-Facility (Office - POS 11):")
    print(f"  Work RVU: {repriced_office.lines[0].work_rvu:.2f}")
    print(f"  PE RVU:   {repriced_office.lines[0].pe_rvu:.2f}")
    print(f"  MP RVU:   {repriced_office.lines[0].mp_rvu:.2f}")
    print(f"  Allowed:  ${repriced_office.total_allowed:.2f}")

    print(f"\nFacility (Hospital Outpatient - POS 22):")
    print(f"  Work RVU: {repriced_hospital.lines[0].work_rvu:.2f}")
    print(f"  PE RVU:   {repriced_hospital.lines[0].pe_rvu:.2f}")
    print(f"  MP RVU:   {repriced_hospital.lines[0].mp_rvu:.2f}")
    print(f"  Allowed:  ${repriced_hospital.total_allowed:.2f}")

    difference = repriced_office.total_allowed - repriced_hospital.total_allowed
    print(f"\nDifference: ${difference:.2f} (Office pays ${difference:.2f} more due to higher PE)")
    print()


def example_4_modifiers():
    """Example 4: Professional and technical components."""
    print("=" * 80)
    print("Example 4: Modifiers (Professional vs Technical Components)")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM004",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="71046",  # Chest X-ray, 2 views
                modifiers=None,
                place_of_service="22",  # Hospital outpatient
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="71046",
                modifiers=["26"],  # Professional component only
                place_of_service="22",
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=3,
                procedure_code="71046",
                modifiers=["TC"],  # Technical component only
                place_of_service="22",
                locality="00",
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nProcedure: 71046 (Chest X-ray, 2 views)")
    print(f"\n{'Modifier':<15} {'Description':<40} {'Allowed':<12}")
    print("-" * 80)

    descriptions = {
        None: "Global (both professional and technical)",
        "26": "Professional component (reading only)",
        "TC": "Technical component (equipment/staff)"
    }

    for line in repriced.lines:
        modifier_key = line.modifiers[0] if line.modifiers and len(line.modifiers) > 0 else None
        desc = descriptions.get(modifier_key, "")
        modifier_display = modifier_key if modifier_key else "None"
        print(f"{modifier_display:<15} {desc:<40} ${line.medicare_allowed:>10.2f}")

    print(f"\nNote: Global = Professional + Technical")
    print()


def example_5_multiple_procedures():
    """Example 5: Multiple procedures with MPPR."""
    print("=" * 80)
    print("Example 5: Multiple Procedures with MPPR")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM005",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="12001",  # Simple repair, 2.5 cm or less
                modifiers=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="12002",  # Simple repair, 2.6 to 7.5 cm
                modifiers=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nMultiple surgical procedures on same day:")
    print(f"\n{'Line':<6} {'Procedure':<12} {'Description':<40} {'Allowed':<12}")
    print("-" * 80)

    descriptions = {
        "12001": "Simple repair, superficial wounds, ≤2.5 cm",
        "12002": "Simple repair, superficial wounds, 2.6-7.5 cm"
    }

    for line in repriced.lines:
        desc = descriptions.get(line.procedure_code, "")
        print(f"{line.line_number:<6} {line.procedure_code:<12} {desc:<40} ${line.medicare_allowed:>10.2f}")
        if line.adjustment_reason:
            print(f"       Note: {line.adjustment_reason}")

    print(f"\n{'Total Medicare Allowed:':<60} ${repriced.total_allowed:>10.2f}")
    print(f"\nNotes:")
    for note in repriced.notes:
        print(f"  - {note}")
    print()


def example_6_query_fee_schedule():
    """Example 6: Querying fee schedule information."""
    print("=" * 80)
    print("Example 6: Querying Fee Schedule Information")
    print("=" * 80)

    repricer = MedicareRepricer()

    # Get procedure information
    procedure_code = "99214"
    proc_info = repricer.get_procedure_info(procedure_code)

    print(f"\nProcedure Code: {procedure_code}")
    print(f"Description: {proc_info['description']}")
    print(f"\nNon-Facility RVUs:")
    print(f"  Work: {proc_info['work_rvu_non_facility']:.2f}")
    print(f"  PE:   {proc_info['pe_rvu_non_facility']:.2f}")
    print(f"  MP:   {proc_info['mp_rvu_non_facility']:.2f}")
    print(f"\nFacility RVUs:")
    print(f"  Work: {proc_info['work_rvu_facility']:.2f}")
    print(f"  PE:   {proc_info['pe_rvu_facility']:.2f}")
    print(f"  MP:   {proc_info['mp_rvu_facility']:.2f}")
    print(f"\nConversion Factor: ${proc_info['conversion_factor']:.4f}")

    # Get locality information
    locality = "01"
    loc_info = repricer.get_locality_info(locality)

    print(f"\n\nLocality: {locality} - {loc_info['locality_name']}")
    print(f"GPCI Values:")
    print(f"  Work: {loc_info['work_gpci']:.3f}")
    print(f"  PE:   {loc_info['pe_gpci']:.3f}")
    print(f"  MP:   {loc_info['mp_gpci']:.3f}")
    print()


def example_7_two_modifiers():
    """Example 7: Using two modifiers on a single procedure."""
    print("=" * 80)
    print("Example 7: Multiple Modifiers (Two Modifiers on One Line)")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM007",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",  # Office visit
                modifiers=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="99214",  # Office visit with modifiers
                modifiers=["50", "59"],  # Bilateral + Distinct procedural service
                place_of_service="11",
                locality="00",
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nProcedure: 99214 (Office visit, established patient)")
    print(f"\n{'Line':<6} {'Modifiers':<20} {'Description':<35} {'Allowed':<12}")
    print("-" * 80)

    descriptions = {
        1: "No modifiers (standard payment)",
        2: "Modifiers 50 + 59 (bilateral + distinct)"
    }

    for line in repriced.lines:
        modifiers_str = ", ".join(line.modifiers) if line.modifiers else "None"
        desc = descriptions.get(line.line_number, "")
        print(f"{line.line_number:<6} {modifiers_str:<20} {desc:<35} ${line.medicare_allowed:>10.2f}")
        if line.adjustment_reason:
            print(f"       Adjustments: {line.adjustment_reason}")

    print(f"\n{'Total Medicare Allowed:':<65} ${repriced.total_allowed:>10.2f}")
    print(f"\nNote: Modifiers are applied sequentially")
    print()


def example_8_zip_code_to_locality():
    """Example 8: Using zip code instead of locality."""
    print("=" * 80)
    print("Example 8: Zip Code to Locality Mapping")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM008",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",
                modifiers=None,
                place_of_service="11",
                zip_code="10001",  # Manhattan, NY - maps to locality 01
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="99214",
                modifiers=None,
                place_of_service="11",
                zip_code="90210",  # Beverly Hills, CA - maps to locality 18
                units=1
            ),
            ClaimLine(
                line_number=3,
                procedure_code="99214",
                modifiers=None,
                place_of_service="11",
                zip_code="60601",  # Chicago, IL - maps to locality 16
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nProcedure: 99214 (Office visit, established patient)")
    print(f"Demonstrating automatic zip code to locality mapping\n")
    print(f"{'Line':<6} {'Zip Code':<12} {'Locality':<12} {'Location':<20} {'Allowed':<12}")
    print("-" * 80)

    locations = {
        "10001": "Manhattan, NY",
        "90210": "Beverly Hills, CA",
        "60601": "Chicago, IL"
    }

    for line in repriced.lines:
        location = locations.get(line.zip_code, "")
        print(f"{line.line_number:<6} {line.zip_code:<12} {line.locality:<12} {location:<20} ${line.medicare_allowed:>10.2f}")

    print(f"\n{'Total Medicare Allowed:':<65} ${repriced.total_allowed:>10.2f}")
    print(f"\nNote: Zip codes are automatically mapped to Medicare locality codes")
    print(f"      Different localities have different GPCI values, affecting payment")
    print()


def example_9_anesthesia_basic():
    """Example 9: Basic anesthesia claim."""
    print("=" * 80)
    print("Example 9: Basic Anesthesia Claim")
    print("=" * 80)

    # Load repricer with full data including anesthesia
    data_dir = Path(__file__).parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="ANES001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="00100",  # Anesthesia for salivary gland surgery
                modifiers=["AA"],  # Anesthesiologist
                place_of_service="22",  # Outpatient hospital
                locality="00",  # Alabama
                units=1,
                anesthesia_time_minutes=90,  # 1.5 hours
                physical_status_modifier=None,
                anesthesia_modifying_units=None
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"\nAnesthesia Procedure: {line.procedure_code}")
    print(f"Description: Anesthesia for salivary gland surgery")
    print(f"\nPricing Calculation:")
    print(f"  Base Units:      {line.anesthesia_base_units} units")
    print(f"  Time Units:      {line.anesthesia_time_units} units (90 min ÷ 15)")
    print(f"  Modifying Units: {line.anesthesia_modifying_units} units")
    print(f"  Total Units:     {line.anesthesia_total_units} units")
    print(f"  Conversion Factor: ${line.conversion_factor:.2f}")
    print(f"\nMedicare Allowed: ${line.medicare_allowed:.2f}")
    print(f"Calculation: {line.anesthesia_total_units} units × ${line.conversion_factor:.2f} = ${line.medicare_allowed:.2f}")

    if line.adjustment_reason:
        print(f"\nNotes: {line.adjustment_reason}")
    print()


def example_10_anesthesia_complex():
    """Example 10: Complex cardiac anesthesia with physical status."""
    print("=" * 80)
    print("Example 10: Complex Cardiac Anesthesia (CABG)")
    print("=" * 80)

    data_dir = Path(__file__).parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="CABG001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="00562",  # Anesthesia for heart surgery with pump
                modifiers=["AA"],  # Anesthesiologist
                place_of_service="22",
                locality="18",  # Los Angeles
                units=1,
                anesthesia_time_minutes=240,  # 4 hours
                physical_status_modifier="P3",  # Severe systemic disease
                anesthesia_modifying_units=None
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"\nAnesthesia Procedure: {line.procedure_code}")
    print(f"Description: Anesthesia for CABG with cardiopulmonary bypass")
    print(f"Physical Status: P3 (Patient with severe systemic disease)")
    print(f"\nPricing Calculation:")
    print(f"  Base Units:      {line.anesthesia_base_units} units (complex cardiac surgery)")
    print(f"  Time Units:      {line.anesthesia_time_units} units (240 min ÷ 15)")
    print(f"  Modifying Units: {line.anesthesia_modifying_units} units (P3 adds 1 unit)")
    print(f"  Total Units:     {line.anesthesia_total_units} units")
    print(f"  Conversion Factor: ${line.conversion_factor:.2f} (Los Angeles)")
    print(f"\nMedicare Allowed: ${line.medicare_allowed:.2f}")

    if line.adjustment_reason:
        print(f"\nNotes:")
        for note in line.adjustment_reason.split("; "):
            print(f"  - {note}")
    print()


def example_11_anesthesia_emergency():
    """Example 11: Emergency pediatric anesthesia with qualifying circumstances."""
    print("=" * 80)
    print("Example 11: Emergency Pediatric Anesthesia")
    print("=" * 80)

    data_dir = Path(__file__).parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="PED_EMERG001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="00326",  # Anesthesia larynx/trach < 1 yr
                modifiers=["99100", "99140"],  # Extreme age + Emergency
                place_of_service="23",  # Emergency room
                locality="00",
                units=1,
                anesthesia_time_minutes=45,
                physical_status_modifier="P4",  # Life-threatening condition
                anesthesia_modifying_units=None
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"\nAnesthesia Procedure: {line.procedure_code}")
    print(f"Description: Emergency pediatric airway surgery")
    print(f"Physical Status: P4 (Life-threatening systemic disease)")
    print(f"Qualifying Circumstances:")
    print(f"  - 99100: Patient under 1 year of age (+1 unit)")
    print(f"  - 99140: Emergency conditions (+2 units)")
    print(f"\nPricing Calculation:")
    print(f"  Base Units:      {line.anesthesia_base_units} units")
    print(f"  Time Units:      {line.anesthesia_time_units} units (45 min ÷ 15)")
    print(f"  Modifying Units: {line.anesthesia_modifying_units} units")
    print(f"    • P4 physical status: +2 units")
    print(f"    • 99100 (age):        +1 unit")
    print(f"    • 99140 (emergency):  +2 units")
    print(f"  Total Units:     {line.anesthesia_total_units} units")
    print(f"  Conversion Factor: ${line.conversion_factor:.2f}")
    print(f"\nMedicare Allowed: ${line.medicare_allowed:.2f}")
    print()


def example_12_anesthesia_geographic_variation():
    """Example 12: Same anesthesia service in different localities."""
    print("=" * 80)
    print("Example 12: Anesthesia Geographic Variation")
    print("=" * 80)

    data_dir = Path(__file__).parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    # Same procedure in three different locations
    locations = [
        ("10112", "00", "Alabama", 19.31),
        ("01112", "05", "San Francisco", 22.37),
        ("02102", "01", "Alaska", 27.86)
    ]

    print(f"\nProcedure: 01200 (Hip replacement anesthesia)")
    print(f"Time: 120 minutes, P2 physical status\n")
    print(f"{'Locality':<20} {'Conversion Factor':<20} {'Medicare Allowed':<20}")
    print("-" * 80)

    for contractor, locality, name, cf in locations:
        claim = Claim(
            claim_id=f"HIP_{locality}",
            lines=[
                ClaimLine(
                    line_number=1,
                    procedure_code="01200",
                    modifiers=["AA"],
                    place_of_service="22",
                    locality=locality,
                    units=1,
                    anesthesia_time_minutes=120,
                    physical_status_modifier="P2",
                    anesthesia_modifying_units=None
                )
            ]
        )

        repriced = repricer.reprice_claim(claim)
        line = repriced.lines[0]

        print(f"{name:<20} ${line.conversion_factor:<19.2f} ${line.medicare_allowed:>18.2f}")

    print(f"\nNote: Same procedure, same time, but payment varies by locality")
    print(f"      Alaska has highest conversion factor, Alabama has lowest")
    print()


def example_13_mixed_claim():
    """Example 13: Claim with both anesthesia and regular procedures."""
    print("=" * 80)
    print("Example 13: Mixed Claim (Anesthesia + Surgery)")
    print("=" * 80)

    data_dir = Path(__file__).parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="MIXED001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="00562",  # Anesthesia for heart surgery
                modifiers=["AA"],
                place_of_service="22",
                locality="00",
                units=1,
                anesthesia_time_minutes=180,
                physical_status_modifier="P3",
                anesthesia_modifying_units=None
            ),
            ClaimLine(
                line_number=2,
                procedure_code="99213",  # Post-op office visit
                modifiers=None,
                place_of_service="11",
                locality="00",
                units=1
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"\n{'Line':<6} {'Code':<10} {'Type':<15} {'Description':<35} {'Allowed':<12}")
    print("-" * 80)

    descriptions = {
        "00562": "Anesthesia for heart surgery with pump",
        "99213": "Office visit, established patient"
    }

    for line in repriced.lines:
        desc = descriptions.get(line.procedure_code, "")
        print(f"{line.line_number:<6} {line.procedure_code:<10} {line.service_type:<15} {desc:<35} ${line.medicare_allowed:>10.2f}")

        if line.service_type == "ANESTHESIA":
            print(f"       Anesthesia details: {line.anesthesia_base_units} base + {line.anesthesia_time_units} time + {line.anesthesia_modifying_units} modifying = {line.anesthesia_total_units} units")

    print(f"\n{'Total Medicare Allowed:':<70} ${repriced.total_allowed:>10.2f}")
    print(f"\nNote: System automatically routes anesthesia codes to anesthesia calculator")
    print(f"      and regular procedure codes to the standard PFS calculator")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("=" * 80)
    print("MEDICARE REPRICING INTERFACE - EXAMPLE USAGE")
    print("=" * 80)
    print()

    # Standard PFS examples
    example_1_simple_office_visit()
    example_2_geographic_variation()
    example_3_facility_vs_non_facility()
    example_4_modifiers()
    example_5_multiple_procedures()
    example_6_query_fee_schedule()
    example_7_two_modifiers()
    example_8_zip_code_to_locality()

    # Anesthesia examples
    print("\n")
    print("=" * 80)
    print("ANESTHESIA PRICING EXAMPLES")
    print("=" * 80)
    print()

    example_9_anesthesia_basic()
    example_10_anesthesia_complex()
    example_11_anesthesia_emergency()
    example_12_anesthesia_geographic_variation()
    example_13_mixed_claim()

    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
