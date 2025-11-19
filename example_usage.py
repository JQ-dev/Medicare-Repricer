"""
Example usage of the Medicare Repricing Interface.

This script demonstrates how to use the Medicare repricing system
with various scenarios.
"""

from medicare_repricing import MedicareRepricer, Claim, ClaimLine


def example_1_simple_office_visit():
    """Example 1: Simple office visit with lab work."""
    print("=" * 80)
    print("Example 1: Simple Office Visit with Lab Work")
    print("=" * 80)

    repricer = MedicareRepricer()

    claim = Claim(
        claim_id="CLM001",
        patient_id="PAT001",
        diagnosis_codes=["I10", "E11.9"],  # Hypertension, Type 2 diabetes
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99213",  # Office visit, established patient
                modifier=None,
                place_of_service="11",  # Office
                locality="00",  # National average
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="80053",  # Comprehensive metabolic panel
                modifier=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
        ]
    )

    repriced = repricer.reprice_claim(claim)

    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"Patient ID: {repriced.patient_id}")
    print(f"Diagnosis Codes: {', '.join(repriced.diagnosis_codes)}")
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
        patient_id="PAT002",
        diagnosis_codes=["M25.511"],  # Pain in right shoulder
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",
                modifier=None,
                place_of_service="11",
                locality="01",  # Manhattan, NY
                units=1
            ),
        ]
    )

    # Texas (Dallas) - Lower cost area
    claim_tx = Claim(
        claim_id="CLM002-TX",
        patient_id="PAT002",
        diagnosis_codes=["M25.511"],
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99214",
                modifier=None,
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
        patient_id="PAT003",
        diagnosis_codes=["Z00.00"],  # General health examination
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99203",
                modifier=None,
                place_of_service="11",  # Office
                locality="00",
                units=1
            ),
        ]
    )

    # Facility (Hospital Outpatient)
    claim_hospital = Claim(
        claim_id="CLM003-HOSPITAL",
        patient_id="PAT003",
        diagnosis_codes=["Z00.00"],
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="99203",
                modifier=None,
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
        patient_id="PAT004",
        diagnosis_codes=["R05.9"],  # Cough
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="71046",  # Chest X-ray, 2 views
                modifier=None,
                place_of_service="22",  # Hospital outpatient
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="71046",
                modifier="26",  # Professional component only
                place_of_service="22",
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=3,
                procedure_code="71046",
                modifier="TC",  # Technical component only
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
        desc = descriptions.get(line.modifier, "")
        modifier_display = line.modifier if line.modifier else "None"
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
        patient_id="PAT005",
        diagnosis_codes=["S61.001A"],  # Laceration of finger
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="12001",  # Simple repair, 2.5 cm or less
                modifier=None,
                place_of_service="11",
                locality="00",
                units=1
            ),
            ClaimLine(
                line_number=2,
                procedure_code="12002",  # Simple repair, 2.6 to 7.5 cm
                modifier=None,
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


def main():
    """Run all examples."""
    print("\n")
    print("=" * 80)
    print("MEDICARE REPRICING INTERFACE - EXAMPLE USAGE")
    print("=" * 80)
    print()

    example_1_simple_office_visit()
    example_2_geographic_variation()
    example_3_facility_vs_non_facility()
    example_4_modifiers()
    example_5_multiple_procedures()
    example_6_query_fee_schedule()

    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
