"""
MS-DRG Grouper Usage Examples

This script demonstrates how to use the MS-DRG Grouper to assign
Medicare Severity Diagnosis Related Groups to inpatient hospital stays.
"""

from pathlib import Path
from medicare_repricing import MSDRGGrouper, GrouperInput, MedicareRepricer, Claim, ClaimLine


def example_1_basic_grouping():
    """Example 1: Basic MS-DRG grouping for a simple case."""
    print("=" * 70)
    print("EXAMPLE 1: Basic MS-DRG Grouping")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))

    # Patient with hip replacement surgery
    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="M16.11",  # Primary osteoarthritis, right hip
        secondary_diagnoses=["I10", "E11.9"],  # Hypertension, Type 2 diabetes
        procedures=["0SR9019"],  # Hip replacement with metal implant
        age=72,
        sex="F"
    ))

    print(f"\nPatient: 72-year-old female")
    print(f"Principal Diagnosis: M16.11 (Primary osteoarthritis, right hip)")
    print(f"Procedure: 0SR9019 (Hip replacement)")
    print(f"\nGrouping Result:")
    print(f"  MS-DRG: {result.ms_drg} - {result.drg_description}")
    print(f"  MDC: {result.mdc} ({result.mdc_description})")
    print(f"  DRG Type: {result.drg_type}")
    print(f"  Has MCC: {result.has_mcc}")
    print(f"  Has CC: {result.has_cc}")
    print(f"  Relative Weight: {result.relative_weight}")
    print(f"  Geometric Mean LOS: {result.geometric_mean_los} days")
    print()


def example_2_complex_medical_case():
    """Example 2: Complex medical case with multiple comorbidities."""
    print("=" * 70)
    print("EXAMPLE 2: Complex Medical Case with MCC")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))

    # Patient with sepsis and multiple complications
    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="A41.9",  # Sepsis, unspecified organism
        secondary_diagnoses=[
            "R65.20",  # Severe sepsis without septic shock (MCC)
            "N17.9",   # Acute kidney failure (MCC)
            "J96.00",  # Acute respiratory failure (MCC)
            "D62",     # Acute posthemorrhagic anemia (CC)
        ],
        age=82,
        sex="M",
        discharge_status="01"  # Discharged home
    ))

    print(f"\nPatient: 82-year-old male")
    print(f"Principal Diagnosis: A41.9 (Sepsis)")
    print(f"Secondary Diagnoses:")
    print(f"  - R65.20 (Severe sepsis)")
    print(f"  - N17.9 (Acute kidney failure)")
    print(f"  - J96.00 (Acute respiratory failure)")
    print(f"  - D62 (Acute posthemorrhagic anemia)")
    print(f"\nGrouping Result:")
    print(f"  MS-DRG: {result.ms_drg} - {result.drg_description}")
    print(f"  MDC: {result.mdc} ({result.mdc_description})")
    print(f"  DRG Type: {result.drg_type}")
    print(f"  Has MCC: {result.has_mcc}")
    print(f"  MCCs Present: {', '.join(result.mcc_list) if result.mcc_list else 'None'}")
    print(f"  Has CC: {result.has_cc}")
    print(f"  CCs Present: {', '.join(result.cc_list) if result.cc_list else 'None'}")
    print(f"  Relative Weight: {result.relative_weight}")
    print()


def example_3_surgical_cardiac():
    """Example 3: Major cardiac surgery (CABG)."""
    print("=" * 70)
    print("EXAMPLE 3: Major Cardiac Surgery (CABG)")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))

    # Patient with coronary artery bypass graft
    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.01",  # STEMI involving left main coronary artery
        secondary_diagnoses=[
            "I50.21",  # Acute systolic heart failure (CC)
            "N17.9",   # Acute kidney failure (MCC)
        ],
        procedures=[
            "02100Z9",  # CABG from left internal mammary artery
        ],
        age=70,
        sex="M",
        length_of_stay=8
    ))

    print(f"\nPatient: 70-year-old male")
    print(f"Principal Diagnosis: I21.01 (STEMI involving left main)")
    print(f"Procedure: 02100Z9 (Coronary bypass)")
    print(f"Length of Stay: 8 days")
    print(f"\nGrouping Result:")
    print(f"  MS-DRG: {result.ms_drg} - {result.drg_description}")
    print(f"  MDC: {result.mdc} ({result.mdc_description})")
    print(f"  DRG Type: {result.drg_type}")
    print(f"  Has MCC: {result.has_mcc}")
    print(f"  Has CC: {result.has_cc}")
    print(f"  Relative Weight: {result.relative_weight}")
    print()


def example_4_integrated_grouping_and_pricing():
    """Example 4: Integrated grouping and pricing workflow."""
    print("=" * 70)
    print("EXAMPLE 4: Integrated Grouping + Pricing Workflow")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))
    repricer = MedicareRepricer(data_directory=Path("../data"))

    # Step 1: Use grouper to assign MS-DRG
    grouping_result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.09",  # STEMI
        secondary_diagnoses=["I50.9", "E11.9"],  # Heart failure (CC) + diabetes
        age=68,
        sex="M"
    ))

    print(f"\nStep 1: MS-DRG Grouping")
    print(f"  Assigned MS-DRG: {grouping_result.ms_drg}")
    print(f"  Description: {grouping_result.drg_description}")
    print(f"  Relative Weight: {grouping_result.relative_weight}")

    # Step 2: Use repricer to calculate payment
    claim = Claim(
        claim_id="INTEGRATED-001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",
                place_of_service="21",
                locality="01",
                ms_drg_code=grouping_result.ms_drg,  # Use DRG from grouper
                provider_number="100001",  # Massachusetts General Hospital
                total_charges=75000.00,
                covered_days=5
            )
        ]
    ))

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nStep 2: IPPS Payment Calculation")
    print(f"  Hospital: {line.hospital_name}")
    print(f"  Base Payment: ${line.base_drg_payment:,.2f}")
    if line.ime_adjustment:
        print(f"  IME Adjustment: ${line.ime_adjustment:,.2f}")
    if line.dsh_adjustment:
        print(f"  DSH Adjustment: ${line.dsh_adjustment:,.2f}")
    if line.outlier_payment:
        print(f"  Outlier Payment: ${line.outlier_payment:,.2f}")
    print(f"  Total Medicare Payment: ${line.medicare_allowed:,.2f}")
    print()


def example_5_severity_comparison():
    """Example 5: Comparing DRG assignment with different severity levels."""
    print("=" * 70)
    print("EXAMPLE 5: DRG Assignment Across Severity Levels")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))

    print("\nSame condition (heart failure) with different comorbidity levels:\n")

    # Case A: Without CC/MCC
    result_a = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I50.9",  # Heart failure
        secondary_diagnoses=[],  # No complications
        age=65,
        sex="M"
    ))
    print(f"A. Without CC/MCC:")
    print(f"   MS-DRG {result_a.ms_drg} - Weight: {result_a.relative_weight}")

    # Case B: With CC
    result_b = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I50.9",  # Heart failure
        secondary_diagnoses=["E87.5"],  # Hyperkalemia (CC)
        age=65,
        sex="M"
    ))
    print(f"B. With CC:")
    print(f"   MS-DRG {result_b.ms_drg} - Weight: {result_b.relative_weight}")

    # Case C: With MCC
    result_c = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I50.9",  # Heart failure
        secondary_diagnoses=["N17.9"],  # Acute kidney failure (MCC)
        age=65,
        sex="M"
    ))
    print(f"C. With MCC:")
    print(f"   MS-DRG {result_c.ms_drg} - Weight: {result_c.relative_weight}")

    print(f"\nNote: Higher severity → Higher relative weight → Higher payment")
    print()


def example_6_batch_processing():
    """Example 6: Batch processing multiple cases."""
    print("=" * 70)
    print("EXAMPLE 6: Batch Processing Multiple Cases")
    print("=" * 70)

    grouper = MSDRGGrouper(data_directory=Path("../data"))

    cases = [
        {
            "patient_id": "PT001",
            "input": GrouperInput(
                principal_diagnosis="M16.11",
                procedures=["0SR9019"],
                age=72,
                sex="F"
            )
        },
        {
            "patient_id": "PT002",
            "input": GrouperInput(
                principal_diagnosis="I21.09",
                secondary_diagnoses=["J96.00"],
                age=68,
                sex="M"
            )
        },
        {
            "patient_id": "PT003",
            "input": GrouperInput(
                principal_diagnosis="A41.9",
                secondary_diagnoses=["R65.20", "N17.9"],
                age=82,
                sex="M"
            )
        },
    ]

    print(f"\nProcessing {len(cases)} cases:\n")
    print(f"{'Patient':<10} {'MS-DRG':<10} {'Type':<12} {'Weight':<8} {'Description':<40}")
    print("-" * 90)

    for case in cases:
        result = grouper.assign_drg(case["input"])
        print(f"{case['patient_id']:<10} {result.ms_drg:<10} {result.drg_type:<12} "
              f"{result.relative_weight:<8.4f} {result.drg_description[:40]:<40}")

    print()


if __name__ == "__main__":
    # Run all examples
    example_1_basic_grouping()
    example_2_complex_medical_case()
    example_3_surgical_cardiac()
    example_4_integrated_grouping_and_pricing()
    example_5_severity_comparison()
    example_6_batch_processing()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
