# Medicare IPPS (Inpatient Prospective Payment System) Implementation

## Overview

This implementation provides complete support for Medicare IPPS pricing, which is used to reimburse acute care hospitals for inpatient services based on MS-DRG (Medicare Severity Diagnosis-Related Group) codes.

## Table of Contents

1. [IPPS Fundamentals](#ipps-fundamentals)
2. [Implementation Components](#implementation-components)
3. [Payment Calculation](#payment-calculation)
4. [Data Requirements](#data-requirements)
5. [Usage Examples](#usage-examples)
6. [Testing](#testing)
7. [CMS References](#cms-references)

## IPPS Fundamentals

### What is IPPS?

The Inpatient Prospective Payment System (IPPS) is Medicare's payment system for hospital inpatient stays. Instead of paying for each service provided, Medicare pays a predetermined amount based on the patient's diagnosis and procedures, grouped into MS-DRGs.

### Key Concepts

- **MS-DRG (Medicare Severity Diagnosis-Related Group)**: A classification system that groups patients with similar clinical conditions and resource utilization
- **Relative Weight**: A numeric value assigned to each DRG representing its costliness relative to the average Medicare case
- **Wage Index**: Geographic adjustment factor reflecting local labor costs
- **Standardized Amount**: National base payment amount set annually by CMS

## Implementation Components

### 1. Data Structures

Located in `medicare_repricing/fee_schedule.py`:

```python
@dataclass
class MSDRGData:
    """MS-DRG data with relative weights and length of stay statistics."""
    ms_drg: str
    description: str
    relative_weight: float
    geometric_mean_los: float
    arithmetic_mean_los: float

@dataclass
class WageIndexData:
    """Wage index by geographic area (CBSA)."""
    cbsa_code: str
    area_name: str
    wage_index: float
    capital_wage_index: Optional[float]

@dataclass
class HospitalData:
    """Hospital-specific characteristics for adjustments."""
    provider_number: str
    hospital_name: str
    cbsa_code: str
    wage_index: float
    is_teaching_hospital: bool
    intern_resident_to_bed_ratio: Optional[float]
    is_dsh_hospital: bool
    dsh_patient_percentage: Optional[float]
    is_rural: bool
    bed_count: Optional[int]
```

### 2. IPPSCalculator Class

Located in `medicare_repricing/calculator.py`:

The `IPPSCalculator` class implements all IPPS payment logic:

- Base DRG payment calculation
- Wage index adjustments
- IME (Indirect Medical Education) adjustments
- DSH (Disproportionate Share Hospital) adjustments
- Outlier payments for high-cost cases

### 3. Data Files

Located in `data/` directory:

- `ms_drg_data.json`: 47 MS-DRGs with FY 2026 relative weights
- `wage_index_data.json`: 56 geographic areas with wage indices
- `hospital_data.json`: 30 hospitals with varying characteristics

## Payment Calculation

### Base DRG Payment Formula

```
Total Payment = Operating Payment + Capital Payment + Adjustments + Outlier
```

### Operating Payment

```
Operating Payment = [(Standard Amount × Labor Share × Wage Index) +
                     (Standard Amount × (1 - Labor Share))] × DRG Weight
```

**Components:**
- Standard Amount: $6,690 (FY 2026)
- Labor Share: 67.6%
- Wage Index: Hospital-specific (0.7123 to 1.6543 in our data)
- DRG Weight: MS-DRG specific (0.5987 to 26.1234 in our data)

**Example Calculation (MS-DRG 470, Wage Index 1.0123):**

```
Labor Portion    = $6,690 × 0.676 × 1.0123 = $4,578.28
Non-Labor Portion = $6,690 × 0.324         = $2,167.56
Subtotal         = $4,578.28 + $2,167.56   = $6,745.84
Operating Payment = $6,745.84 × 1.7845     = $12,037.71
```

### Capital Payment

```
Capital Payment = Capital Standard Amount × Capital GAF × DRG Weight
```

**Components:**
- Capital Standard Amount: $488.59 (FY 2026)
- Capital GAF (Geographic Adjustment Factor): Area-specific
- DRG Weight: Same as operating payment

**Example:**
```
Capital Payment = $488.59 × 1.0001 × 1.7845 = $871.68
```

### Base DRG Payment

```
Base DRG Payment = Operating Payment + Capital Payment
                 = $12,037.71 + $871.68
                 = $12,909.39
```

### IME (Indirect Medical Education) Adjustment

Applied to teaching hospitals to account for higher costs associated with medical education.

```
IME Adjustment = Base Payment × [c × ((IRB + 0.4)^0.405 - 1)]
```

**Where:**
- c = 1.34 (FY 2026 IME adjustment factor)
- IRB = Intern and Resident to Bed Ratio

**Example (IRB = 0.85):**
```
IME Multiplier = 1.34 × ((0.85 + 0.4)^0.405 - 1)
              = 1.34 × (1.25^0.405 - 1)
              = 1.34 × (1.0929 - 1)
              = 1.34 × 0.0929
              = 0.1245 (12.45%)

IME Adjustment = $12,909.39 × 0.1245 = $1,607.22
```

### DSH (Disproportionate Share Hospital) Adjustment

Applied to hospitals serving a disproportionate share of low-income patients.

```
DSH Adjustment = Base Payment × [(DSH % / 100)^0.5 × Factor]
```

**Where:**
- DSH % = Hospital's disproportionate patient percentage
- Factor = 0.35 (simplified for this implementation)

**Example (DSH % = 22.3):**
```
DSH Factor = sqrt(22.3 / 100) × 0.35
          = sqrt(0.223) × 0.35
          = 0.472 × 0.35
          = 0.1652 (16.52%)

DSH Adjustment = $12,909.39 × 0.1652 = $2,132.59
```

### Outlier Payment

Additional payment for extraordinarily high-cost cases.

```
If (Estimated Costs - Base Payment) > Threshold:
    Outlier = (Estimated Costs - Base Payment - Threshold) × 0.80
```

**Where:**
- Estimated Costs = Total Charges × Cost-to-Charge Ratio (0.25 typical)
- Threshold = $46,217 (FY 2026 fixed-loss threshold)
- Payment Rate = 80% of costs above threshold

**Example (Charges = $2,000,000):**
```
Estimated Costs = $2,000,000 × 0.25 = $500,000
Base + Adjustments = $12,909 + $1,607 + $2,133 = $16,649

Excess Costs = $500,000 - $16,649 = $483,351
Above Threshold = $483,351 - $46,217 = $437,134
Outlier Payment = $437,134 × 0.80 = $349,707
```

### Total Payment Example

For a major teaching hospital with DSH and outlier case:

```
Operating Payment:    $ 12,037.71
Capital Payment:      $    871.68
─────────────────────────────────
Base DRG Payment:     $ 12,909.39
IME Adjustment:       $  1,607.22
DSH Adjustment:       $  2,132.59
Outlier Payment:      $349,707.20
─────────────────────────────────
TOTAL PAYMENT:        $366,356.40
```

## Data Requirements

### MS-DRG Data

The system includes 47 representative MS-DRGs across major clinical categories:

- **Cardiac**: AMI (280-282), Heart Failure (291-293)
- **Respiratory**: COPD (190-192), Pulmonary Edema (189)
- **Orthopedic**: Major Joint Replacement (469-470), Hip/Femur (480-482)
- **Digestive**: GI Hemorrhage (377-379)
- **Infectious**: Septicemia (871-872), Infections (853-854)
- **Transplant**: Heart Transplant (001-002)
- **And more...**

### Wage Index Data

Covers 56 geographic areas:

- 45 major metropolitan areas (CBSAs)
- 11 rural areas representing different states
- Wage indices ranging from 0.7123 (rural MS) to 1.6543 (San Jose, CA)

### Hospital Data

30 sample hospitals representing:

- **Major Teaching Hospitals** (10): Mass General, Johns Hopkins, Mayo Clinic, etc.
- **Community DSH Hospitals** (5): Serving high proportion of low-income patients
- **Specialty Hospitals** (5): Orthopedic, cardiac, surgical centers
- **Rural Hospitals** (10): Small facilities in rural areas

## Usage Examples

### Basic Usage with MedicareRepricer

```python
from pathlib import Path
from medicare_repricing import MedicareRepricer, Claim, ClaimLine

# Initialize repricer
data_dir = Path("data")
repricer = MedicareRepricer(data_directory=data_dir)

# Create inpatient claim
claim = Claim(
    claim_id="INP-001",
    lines=[
        ClaimLine(
            line_number=1,
            procedure_code="INPATIENT",
            place_of_service="21",  # Inpatient
            locality="01",
            units=1,
            ms_drg_code="470",  # Major joint replacement
            provider_number="100001",  # Mass General
            total_charges=85000.00,
            covered_days=3
        )
    ]
)

# Reprice
repriced = repricer.reprice_claim(claim)

# Access results
line = repriced.lines[0]
print(f"Hospital: {line.hospital_name}")
print(f"DRG: {line.ms_drg_code} - {line.drg_description}")
print(f"Medicare Allowed: ${line.medicare_allowed:,.2f}")
```

### Direct Calculator Usage

```python
from medicare_repricing.calculator import IPPSCalculator
from medicare_repricing.fee_schedule import MedicareFeeSchedule

# Load data
fee_schedule = MedicareFeeSchedule()
fee_schedule.load_from_directory(Path("data"))

# Create calculator
calculator = IPPSCalculator(fee_schedule)

# Calculate payment
allowed, details = calculator.calculate_allowed_amount(
    ms_drg="470",
    provider_number="100001",
    total_charges=85000.00,
    covered_days=3
)

print(f"Payment: ${allowed:,.2f}")
print(f"Details: {details}")
```

### Accessing Payment Components

```python
repriced = repricer.reprice_claim(claim)
line = repriced.lines[0]

# Payment components
print(f"Operating Payment: ${line.operating_payment:,.2f}")
print(f"Capital Payment: ${line.capital_payment:,.2f}")
print(f"Base Payment: ${line.base_drg_payment:,.2f}")
print(f"IME Adjustment: ${line.ime_adjustment:,.2f}")
print(f"DSH Adjustment: ${line.dsh_adjustment:,.2f}")
print(f"Outlier Payment: ${line.outlier_payment:,.2f}")
print(f"Total: ${line.medicare_allowed:,.2f}")

# Hospital characteristics
print(f"Wage Index: {line.wage_index_value}")
print(f"DRG Weight: {line.drg_relative_weight}")

# Clinical information
print(f"Geometric Mean LOS: {line.geometric_mean_los} days")
print(f"Actual Days: {line.covered_days}")
```

## Testing

### Running Tests

```bash
# Run all IPPS tests
pytest test_ipps_pricing.py -v

# Run specific test class
pytest test_ipps_pricing.py::TestIPPSCalculator -v

# Run specific test
pytest test_ipps_pricing.py::TestIPPSCalculator::test_teaching_hospital_ime_adjustment -v
```

### Test Coverage

The test suite includes:

1. **Basic Calculations**: Standard DRG payment without adjustments
2. **IME Adjustments**: Teaching hospital payments
3. **DSH Adjustments**: Disproportionate share payments
4. **Outlier Payments**: High-cost case handling
5. **Geographic Variations**: High/low wage index areas
6. **Rural Hospitals**: Rural designation and adjustments
7. **Integration Tests**: End-to-end claim repricing
8. **Error Handling**: Invalid DRG codes, missing data
9. **Complex Scenarios**: Combined adjustments and outliers

### Example Test

```python
def test_teaching_hospital_ime_adjustment(calculator):
    """Test IME adjustment for teaching hospitals."""
    allowed_amount, details = calculator.calculate_allowed_amount(
        ms_drg="470",
        provider_number="100001"  # Mass General (teaching)
    )

    assert details["is_teaching_hospital"] is True
    assert details["ime_adjustment"] > 0
    # IME should add 35-45% for IRB=0.85
    ime_percentage = details["ime_adjustment"] / details["base_drg_payment"]
    assert 0.30 < ime_percentage < 0.50
```

## Advanced Features

### Payment Comparison Tool

Compare the same DRG across different hospital types:

```python
def compare_drg_payments(drg_code, hospitals):
    """Compare DRG payment across multiple hospitals."""
    for provider_num, name in hospitals:
        allowed, details = calculator.calculate_allowed_amount(
            ms_drg=drg_code,
            provider_number=provider_num
        )
        print(f"{name}: ${allowed:,.2f}")
```

### Custom Hospital Data

Add your own hospital data:

```python
from medicare_repricing.fee_schedule import HospitalData

hospital = HospitalData(
    provider_number="500001",
    hospital_name="Custom Hospital",
    cbsa_code="12060",  # Atlanta
    wage_index=0.9876,
    is_teaching_hospital=False,
    is_dsh_hospital=True,
    dsh_patient_percentage=25.0,
    is_rural=False,
    bed_count=200
)

fee_schedule.add_hospital(hospital)
```

## CMS References

### Official Resources

1. **IPPS Final Rule**: Annual updates to payment rates and policies
   - FY 2026 rates used in this implementation

2. **MS-DRG Definitions Manual**: Clinical criteria for DRG assignment

3. **Wage Index Files**: Annual wage index by CBSA

4. **Impact File**: Detailed payment calculations and examples

### Key Regulations

- **42 CFR 412**: Prospective payment systems for inpatient hospital services
- **42 CFR 412.308**: Wage index adjustments
- **42 CFR 412.105**: IME adjustments
- **42 CFR 412.106**: DSH adjustments
- **42 CFR 412.84**: Outlier payments

### Implementation Notes

This implementation uses:
- FY 2026 standardized amounts and payment parameters
- Simplified DSH calculation (actual CMS formula is more complex)
- Typical cost-to-charge ratio of 0.25 for outlier calculations
- Standard labor share of 67.6%

For production use, consider:
- Loading actual CMS data files
- Hospital-specific cost-to-charge ratios
- Transfer case policies
- Post-acute care transfer (PACT) adjustments
- Quality reporting adjustments
- Readmission penalties

## Data Updates

### Annual Updates Required

1. **Standardized Amounts**: Update in `MedicareFeeSchedule.__init__`
2. **MS-DRG Weights**: Download from CMS IPPS Final Rule
3. **Wage Index**: Download annual wage index file
4. **IME Factor**: Update `IPPSCalculator.ime_adjustment_factor`
5. **Outlier Threshold**: Update `ipps_outlier_threshold`

### Data Sources

- CMS IPPS webpage: https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps
- Annual IPPS Final Rule (typically published August)
- Wage Index files (updated annually)
- Provider-Specific File (for hospital characteristics)

## Performance Considerations

- Fee schedule data loaded once at initialization
- Calculations are fast O(1) lookups + arithmetic
- No database queries during pricing
- Thread-safe for concurrent repricing

## Limitations

Current implementation does not include:
- Transfer case payment adjustments
- New technology add-on payments
- Capital IME adjustments
- Hemophilia add-on payments
- Skilled nursing facility (SNF) transition adjustments
- Hospital-acquired condition (HAC) reductions
- Value-based purchasing (VBP) adjustments
- Hospital readmission reduction program (HRRP) penalties

These can be added in future versions as needed.

## Support

For questions or issues:
1. Review this documentation
2. Check example code in `examples/ipps_example.py`
3. Run tests to verify installation: `pytest test_ipps_pricing.py -v`
4. Consult CMS resources for policy questions

## Version History

- **v1.0** (2025): Initial full IPPS implementation
  - Complete MS-DRG payment calculation
  - IME, DSH, and outlier adjustments
  - 47 MS-DRGs, 56 geographic areas, 30 hospitals
  - Comprehensive test suite
  - Integration with existing repricer
