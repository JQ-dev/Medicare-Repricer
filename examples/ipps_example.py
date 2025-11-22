"""
Example usage of Medicare IPPS (Inpatient Prospective Payment System) pricing.

This demonstrates how to reprice inpatient hospital claims using MS-DRG codes
and hospital-specific data.
"""

from pathlib import Path
from medicare_repricing import MedicareRepricer, Claim, ClaimLine


def example_basic_inpatient_stay():
    """
    Example 1: Basic inpatient hospital stay.

    Scenario: Patient undergoes major joint replacement at a community hospital.
    """
    print("=" * 80)
    print("Example 1: Basic Inpatient Stay - Major Joint Replacement")
    print("=" * 80)

    # Initialize repricer with data directory
    data_dir = Path(__file__).parent.parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    # Create inpatient claim
    claim = Claim(
        claim_id="INP-2024-001",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",  # Placeholder for inpatient stay
                place_of_service="21",  # Inpatient hospital
                locality="01",
                units=1,
                ms_drg_code="470",  # Major joint replacement without MCC
                provider_number="300001",  # Scottsdale Surgical Hospital
                total_charges=75000.00,
                covered_days=3
            )
        ]
    )

    # Reprice the claim
    repriced = repricer.reprice_claim(claim)

    # Display results
    line = repriced.lines[0]
    print(f"\nClaim ID: {repriced.claim_id}")
    print(f"Hospital: {line.hospital_name}")
    print(f"MS-DRG: {line.ms_drg_code} - {line.drg_description}")
    print(f"DRG Weight: {line.drg_relative_weight}")
    print(f"Wage Index: {line.wage_index_value}")
    print(f"\nPayment Breakdown:")
    print(f"  Operating Payment: ${line.operating_payment:,.2f}")
    print(f"  Capital Payment:   ${line.capital_payment:,.2f}")
    print(f"  Base DRG Payment:  ${line.base_drg_payment:,.2f}")
    print(f"  IME Adjustment:    ${line.ime_adjustment:,.2f}")
    print(f"  DSH Adjustment:    ${line.dsh_adjustment:,.2f}")
    print(f"  Outlier Payment:   ${line.outlier_payment:,.2f}")
    print(f"\n  TOTAL ALLOWED:     ${line.medicare_allowed:,.2f}")
    print(f"\nCovered Days: {line.covered_days}")
    print(f"Geometric Mean LOS: {line.geometric_mean_los} days")


def example_teaching_hospital():
    """
    Example 2: Teaching hospital with IME adjustment.

    Scenario: Complex cardiac case at a major teaching hospital.
    """
    print("\n" + "=" * 80)
    print("Example 2: Teaching Hospital - Cardiac Case")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="INP-2024-002",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",
                place_of_service="21",
                locality="01",
                units=1,
                ms_drg_code="280",  # Acute myocardial infarction with MCC
                provider_number="100001",  # Massachusetts General Hospital (teaching)
                total_charges=125000.00,
                covered_days=5
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nHospital: {line.hospital_name}")
    print(f"MS-DRG: {line.ms_drg_code} - {line.drg_description}")
    print(f"\nPayment Breakdown:")
    print(f"  Base DRG Payment:  ${line.base_drg_payment:,.2f}")
    print(f"  IME Adjustment:    ${line.ime_adjustment:,.2f} (Teaching Hospital)")
    print(f"  DSH Adjustment:    ${line.dsh_adjustment:,.2f}")
    print(f"\n  TOTAL ALLOWED:     ${line.medicare_allowed:,.2f}")

    # Calculate IME percentage
    ime_percentage = (line.ime_adjustment / line.base_drg_payment) * 100
    print(f"\nIME adds {ime_percentage:.1f}% to base payment")


def example_dsh_hospital():
    """
    Example 3: DSH (Disproportionate Share Hospital) adjustment.

    Scenario: Patient treated at hospital serving high proportion of low-income patients.
    """
    print("\n" + "=" * 80)
    print("Example 3: DSH Hospital - Septicemia Case")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="INP-2024-003",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",
                place_of_service="21",
                locality="01",
                units=1,
                ms_drg_code="871",  # Septicemia without MV >96 hours with MCC
                provider_number="200001",  # Atlanta Regional Medical Center (DSH)
                total_charges=95000.00,
                covered_days=7
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nHospital: {line.hospital_name}")
    print(f"MS-DRG: {line.ms_drg_code} - {line.drg_description}")
    print(f"\nPayment Breakdown:")
    print(f"  Base DRG Payment:  ${line.base_drg_payment:,.2f}")
    print(f"  DSH Adjustment:    ${line.dsh_adjustment:,.2f} (Disproportionate Share)")
    print(f"\n  TOTAL ALLOWED:     ${line.medicare_allowed:,.2f}")

    # Calculate DSH percentage
    dsh_percentage = (line.dsh_adjustment / line.base_drg_payment) * 100
    print(f"\nDSH adds {dsh_percentage:.1f}% to base payment")


def example_outlier_case():
    """
    Example 4: High-cost case with outlier payment.

    Scenario: Extremely complex case with costs far exceeding typical DRG payment.
    """
    print("\n" + "=" * 80)
    print("Example 4: Outlier Case - Heart Transplant")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="INP-2024-004",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",
                place_of_service="21",
                locality="01",
                units=1,
                ms_drg_code="001",  # Heart transplant with MCC
                provider_number="100007",  # NewYork-Presbyterian (teaching + DSH)
                total_charges=2500000.00,  # Very high charges
                covered_days=45
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nHospital: {line.hospital_name}")
    print(f"MS-DRG: {line.ms_drg_code} - {line.drg_description}")
    print(f"DRG Weight: {line.drg_relative_weight}")
    print(f"Total Charges: ${claim.lines[0].total_charges:,.2f}")
    print(f"\nPayment Breakdown:")
    print(f"  Base DRG Payment:  ${line.base_drg_payment:,.2f}")
    print(f"  IME Adjustment:    ${line.ime_adjustment:,.2f}")
    print(f"  DSH Adjustment:    ${line.dsh_adjustment:,.2f}")
    print(f"  Outlier Payment:   ${line.outlier_payment:,.2f} (High-Cost Case)")
    print(f"\n  TOTAL ALLOWED:     ${line.medicare_allowed:,.2f}")
    print(f"\nCovered Days: {line.covered_days}")
    print(f"Geometric Mean LOS: {line.geometric_mean_los} days")


def example_rural_hospital():
    """
    Example 5: Rural hospital with low wage index.

    Scenario: Patient treated at rural hospital with DSH designation.
    """
    print("\n" + "=" * 80)
    print("Example 5: Rural Hospital - Hip Fracture")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data"
    repricer = MedicareRepricer(data_directory=data_dir)

    claim = Claim(
        claim_id="INP-2024-005",
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code="INPATIENT",
                place_of_service="21",
                locality="01",
                units=1,
                ms_drg_code="480",  # Hip and femur procedures with MCC
                provider_number="400002",  # Mississippi Delta Regional (rural DSH)
                total_charges=68000.00,
                covered_days=6
            )
        ]
    )

    repriced = repricer.reprice_claim(claim)
    line = repriced.lines[0]

    print(f"\nHospital: {line.hospital_name}")
    print(f"MS-DRG: {line.ms_drg_code} - {line.drg_description}")
    print(f"Wage Index: {line.wage_index_value} (Rural Area)")
    print(f"\nPayment Breakdown:")
    print(f"  Operating Payment: ${line.operating_payment:,.2f}")
    print(f"  Capital Payment:   ${line.capital_payment:,.2f}")
    print(f"  Base DRG Payment:  ${line.base_drg_payment:,.2f}")
    print(f"  DSH Adjustment:    ${line.dsh_adjustment:,.2f}")
    print(f"\n  TOTAL ALLOWED:     ${line.medicare_allowed:,.2f}")

    if line.adjustment_reason:
        print(f"\nNotes: {line.adjustment_reason}")


def example_direct_calculator_usage():
    """
    Example 6: Using IPPSCalculator directly (advanced).

    Demonstrates direct use of the calculator for custom scenarios.
    """
    print("\n" + "=" * 80)
    print("Example 6: Direct Calculator Usage")
    print("=" * 80)

    from medicare_repricing.calculator import IPPSCalculator
    from medicare_repricing.fee_schedule import MedicareFeeSchedule

    # Load fee schedule
    fee_schedule = MedicareFeeSchedule()
    data_dir = Path(__file__).parent.parent / "data"
    fee_schedule.load_from_directory(data_dir)

    # Create calculator
    calculator = IPPSCalculator(fee_schedule)

    # Calculate for specific scenario
    allowed_amount, details = calculator.calculate_allowed_amount(
        ms_drg="470",
        provider_number="100006",  # UCSF Medical Center
        total_charges=85000.00,
        covered_days=3
    )

    print(f"\nMS-DRG: {details['ms_drg']} - {details['drg_description']}")
    print(f"Hospital: {details['hospital_name']}")
    print(f"Wage Index: {details['wage_index']}")
    print(f"\nCalculation Details:")
    print(f"  DRG Weight:        {details['drg_relative_weight']}")
    print(f"  Operating Payment: ${details['operating_payment']:,.2f}")
    print(f"  Capital Payment:   ${details['capital_payment']:,.2f}")
    print(f"  Base Payment:      ${details['base_drg_payment']:,.2f}")

    if details['is_teaching_hospital']:
        print(f"  IME Adjustment:    ${details['ime_adjustment']:,.2f}")
    if details['is_dsh_hospital']:
        print(f"  DSH Adjustment:    ${details['dsh_adjustment']:,.2f}")
    if details['outlier_payment'] > 0:
        print(f"  Outlier Payment:   ${details['outlier_payment']:,.2f}")

    print(f"\n  Total Allowed:     ${allowed_amount:,.2f}")


def example_comparison_across_hospitals():
    """
    Example 7: Compare same DRG across different hospital types.

    Shows how payment varies by hospital characteristics.
    """
    print("\n" + "=" * 80)
    print("Example 7: DRG Payment Comparison Across Hospital Types")
    print("=" * 80)

    from medicare_repricing.calculator import IPPSCalculator
    from medicare_repricing.fee_schedule import MedicareFeeSchedule

    fee_schedule = MedicareFeeSchedule()
    data_dir = Path(__file__).parent.parent / "data"
    fee_schedule.load_from_directory(data_dir)
    calculator = IPPSCalculator(fee_schedule)

    # Same DRG at different hospital types
    hospitals = [
        ("300001", "Community Specialty"),
        ("100001", "Major Teaching"),
        ("200001", "Community DSH"),
        ("400002", "Rural DSH"),
    ]

    print(f"\nMS-DRG 470 (Major Joint Replacement) Payment Comparison:\n")
    print(f"{'Hospital Type':<25} {'Base Payment':<15} {'Adjustments':<15} {'Total':<15}")
    print("-" * 70)

    for provider_num, hospital_type in hospitals:
        allowed, details = calculator.calculate_allowed_amount(
            ms_drg="470",
            provider_number=provider_num
        )

        adjustments = details['ime_adjustment'] + details['dsh_adjustment']

        print(f"{hospital_type:<25} ${details['base_drg_payment']:>12,.2f}  "
              f"${adjustments:>12,.2f}  ${allowed:>12,.2f}")


if __name__ == "__main__":
    """Run all examples."""

    print("\n")
    print("*" * 80)
    print("Medicare IPPS (Inpatient Prospective Payment System) Examples")
    print("*" * 80)

    example_basic_inpatient_stay()
    example_teaching_hospital()
    example_dsh_hospital()
    example_outlier_case()
    example_rural_hospital()
    example_direct_calculator_usage()
    example_comparison_across_hospitals()

    print("\n" + "*" * 80)
    print("Examples completed!")
    print("*" * 80 + "\n")
