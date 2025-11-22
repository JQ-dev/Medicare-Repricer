# MS-DRG Grouper Documentation

## Overview

The MS-DRG (Medicare Severity Diagnosis Related Groups) Grouper is a standalone module that assigns DRG codes to inpatient hospital stays based on clinical and demographic information. This implementation follows CMS (Centers for Medicare & Medicaid Services) grouping logic for FY 2026.

## Table of Contents

- [What is MS-DRG Grouping?](#what-is-ms-drg-grouping)
- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Data Files](#data-files)
- [API Reference](#api-reference)
- [Integration with IPPS Pricing](#integration-with-ipps-pricing)
- [Extending the Grouper](#extending-the-grouper)
- [Limitations](#limitations)

---

## What is MS-DRG Grouping?

MS-DRG grouping is the process of classifying inpatient hospital stays into payment categories based on:

- **Principal diagnosis** (ICD-10-CM code) - The main condition treated
- **Secondary diagnoses** (ICD-10-CM codes) - Complications/comorbidities
- **Procedures performed** (ICD-10-PCS codes) - Surgical vs. medical care
- **Patient demographics** - Age, sex, discharge status

Each inpatient stay is assigned to ONE of 998 MS-DRGs, which determines the base payment amount under Medicare's Inpatient Prospective Payment System (IPPS).

---

## Features

### Current Capabilities ✅

- **25 Major Diagnostic Categories (MDCs)** - Organ system-based groupings
- **ICD-10-CM Diagnosis Code Processing** - Comprehensive starter set covering common conditions
- **ICD-10-PCS Procedure Code Processing** - OR vs. non-OR procedure classification
- **CC/MCC Determination** - Automatically identifies complications and major complications
- **Surgical vs. Medical DRG Logic** - Separates surgical and medical cases
- **Severity-Based Grouping** - Assigns DRGs based on presence of CC/MCC
- **Full Integration with IPPS Pricer** - Seamless workflow from grouping to payment
- **998 MS-DRG Database** - Complete range with relative weights and length of stay data

### Supported Clinical Scenarios

| MDC | Body System | Example DRGs |
|-----|-------------|--------------|
| 01 | Nervous System | Stroke, seizures, craniotomy |
| 04 | Respiratory System | Pneumonia, COPD, respiratory failure |
| 05 | Circulatory System | AMI, heart failure, CABG, PCI |
| 06 | Digestive System | GI procedures, hemorrhage, obstruction |
| 08 | Musculoskeletal | Hip/knee replacement, spinal fusion |
| 10 | Endocrine/Metabolic | Diabetes, metabolic disorders |
| 11 | Kidney/Urinary Tract | Acute kidney failure, UTI |
| 18 | Infectious Disease | Septicemia, severe sepsis |

---

## Quick Start

### Installation

```python
from pathlib import Path
from medicare_repricing import MSDRGGrouper, GrouperInput

# Initialize the grouper
grouper = MSDRGGrouper(data_directory=Path("data"))
```

### Basic Example

```python
# Assign MS-DRG for a hip replacement patient
result = grouper.assign_drg(GrouperInput(
    principal_diagnosis="M16.11",  # Primary osteoarthritis, right hip
    secondary_diagnoses=["I10", "E11.9"],  # Hypertension, diabetes
    procedures=["0SR9019"],  # Hip replacement procedure
    age=72,
    sex="F"
))

print(f"MS-DRG: {result.ms_drg}")  # Output: 470
print(f"Description: {result.drg_description}")
print(f"Relative Weight: {result.relative_weight}")  # For payment calculation
```

### Medical Case Example

```python
# Sepsis patient with complications
result = grouper.assign_drg(GrouperInput(
    principal_diagnosis="A41.9",  # Sepsis
    secondary_diagnoses=["R65.20", "N17.9"],  # Severe sepsis + AKI (both MCCs)
    age=82,
    sex="M"
))

print(f"MS-DRG: {result.ms_drg}")  # Output: 871 (Septicemia with MCC)
print(f"Has MCC: {result.has_mcc}")  # True
print(f"MCCs: {result.mcc_list}")  # ['R6520', 'N179']
```

---

## How It Works

### Grouping Algorithm Flow

```
┌─────────────────────────────────────────────────┐
│ 1. VALIDATE INPUT                               │
│    - Principal diagnosis required               │
│    - Secondary diagnoses optional               │
│    - Procedures optional                        │
│    - Age, sex required                          │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│ 2. ASSIGN MDC (Major Diagnostic Category)      │
│    - Look up principal diagnosis               │
│    - Determine body system (MDC 01-25)         │
│    - Special logic for MDC 00, 24, 25          │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│ 3. IDENTIFY COMPLICATIONS/COMORBIDITIES        │
│    - Check each secondary diagnosis             │
│    - Classify as CC or MCC                     │
│    - Apply CC exclusion lists                  │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│ 4. DETERMINE SURGICAL VS. MEDICAL              │
│    - Check for OR (Operating Room) procedures  │
│    - Yes → Surgical DRG path                   │
│    - No → Medical DRG path                     │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│ 5. APPLY MDC-SPECIFIC GROUPING RULES           │
│    - Match procedures/diagnoses to DRG family  │
│    - Select DRG based on severity:             │
│      * With MCC (highest severity)             │
│      * With CC (moderate severity)             │
│      * Without CC/MCC (lowest severity)        │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│ 6. RETURN ASSIGNED MS-DRG                      │
│    - DRG code (e.g., "470")                    │
│    - Description, relative weight, GMLOS       │
│    - Grouping details and warnings             │
└─────────────────────────────────────────────────┘
```

### MDC Assignment Examples

| Principal Diagnosis | Code | MDC | Body System |
|---------------------|------|-----|-------------|
| STEMI | I21.09 | 05 | Circulatory System |
| Hip osteoarthritis | M16.11 | 08 | Musculoskeletal |
| Pneumonia | J18.9 | 04 | Respiratory System |
| Sepsis | A41.9 | 18 | Infectious Disease |
| Acute kidney failure | N17.9 | 11 | Kidney/Urinary Tract |

### CC/MCC Classifications

**Major Complications/Comorbidities (MCC)** - Most severe:
- Acute respiratory failure (J96.00, J96.01, J96.02)
- Acute kidney failure (N17.0-N17.9)
- Severe sepsis (R65.20, R65.21)
- STEMI (I21.01-I21.4)
- Acute hepatic failure (K72.00, K72.01)

**Complications/Comorbidities (CC)** - Moderate severity:
- COPD with exacerbation (J44.1)
- Chronic kidney disease stage 3-4 (N18.3, N18.4)
- Acute systolic heart failure (I50.21)
- Pneumonia (J18.9)
- Cerebral infarction (I63.00)

---

## Data Files

The grouper relies on the following data files in the `data/` directory:

### 1. `icd10_cm_data.json`
Contains ICD-10-CM diagnosis codes with MDC assignments and CC/MCC flags.

Structure:
```json
{
  "version": "FY2026_v43",
  "codes": {
    "MDC_05_CIRCULATORY_SYSTEM": {
      "I21.09": {
        "description": "STEMI involving other coronary artery",
        "mdc": "05",
        "is_cc": false,
        "is_mcc": true
      }
    }
  }
}
```

### 2. `icd10_pcs_data.json`
Contains ICD-10-PCS procedure codes with OR/non-OR classifications.

Structure:
```json
{
  "version": "FY2026_v43",
  "procedures": {
    "ORTHOPEDIC_JOINT_REPLACEMENT": {
      "0SR9019": {
        "description": "Replacement of Right Hip Joint...",
        "is_or_procedure": true,
        "is_non_or_procedure": false
      }
    }
  }
}
```

### 3. `mdc_definitions.json`
Defines all 26 Major Diagnostic Categories (00-25).

### 4. `drg_grouping_rules.json`
Contains MDC-specific rules for assigning DRGs based on procedures and diagnoses.

### 5. `ms_drg_data.json`
Contains all 998 MS-DRGs with relative weights, mean length of stay, and descriptions.

---

## API Reference

### `MSDRGGrouper` Class

#### Constructor
```python
MSDRGGrouper(data_directory: Path)
```

**Parameters:**
- `data_directory` - Path to directory containing grouper data files

**Example:**
```python
grouper = MSDRGGrouper(data_directory=Path("data"))
```

#### `assign_drg()` Method
```python
def assign_drg(input_data: GrouperInput) -> GrouperOutput
```

**Parameters:**
- `input_data` - GrouperInput object with clinical and demographic information

**Returns:**
- `GrouperOutput` object with assigned MS-DRG and grouping details

---

### `GrouperInput` Model

```python
class GrouperInput(BaseModel):
    principal_diagnosis: str  # Required
    secondary_diagnoses: Optional[List[str]] = None
    procedures: Optional[List[str]] = None
    age: int  # Required
    sex: str  # Required: 'M', 'F', or 'U'
    discharge_status: Optional[str] = "01"
    length_of_stay: Optional[int] = None
```

**Field Descriptions:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `principal_diagnosis` | str | ✅ | Primary ICD-10-CM diagnosis code | "I21.09" |
| `secondary_diagnoses` | List[str] | ❌ | Secondary ICD-10-CM codes | ["I10", "E11.9"] |
| `procedures` | List[str] | ❌ | ICD-10-PCS procedure codes | ["0SR9019"] |
| `age` | int | ✅ | Patient age in years (0-120) | 72 |
| `sex` | str | ✅ | Patient sex: M/F/U | "F" |
| `discharge_status` | str | ❌ | Discharge disposition code | "01" |
| `length_of_stay` | int | ❌ | Length of stay in days | 5 |

---

### `GrouperOutput` Model

```python
class GrouperOutput(BaseModel):
    ms_drg: str  # Assigned MS-DRG code
    drg_description: str  # DRG description
    mdc: str  # Major Diagnostic Category
    mdc_description: str  # MDC description
    drg_type: str  # "SURGICAL", "MEDICAL", or "PRE-MDC"
    has_mcc: bool  # Presence of Major CC
    has_cc: bool  # Presence of CC (excluding MCCs)
    mcc_list: Optional[List[str]]  # Codes that qualified as MCC
    cc_list: Optional[List[str]]  # Codes that qualified as CC
    relative_weight: Optional[float]  # DRG relative weight
    geometric_mean_los: Optional[float]  # Expected length of stay
    arithmetic_mean_los: Optional[float]  # Average length of stay
    grouping_version: str  # Grouper version
    warning_messages: Optional[List[str]]  # Warnings
    error_messages: Optional[List[str]]  # Errors
```

---

## Integration with IPPS Pricing

The grouper integrates seamlessly with the IPPS pricer for end-to-end workflow:

```python
from pathlib import Path
from medicare_repricing import (
    MSDRGGrouper, GrouperInput,
    MedicareRepricer, Claim, ClaimLine
)

# Step 1: Assign MS-DRG using grouper
grouper = MSDRGGrouper(data_directory=Path("data"))

grouping_result = grouper.assign_drg(GrouperInput(
    principal_diagnosis="I21.09",  # STEMI
    secondary_diagnoses=["J96.00", "N17.9"],  # Resp failure + AKI
    age=68,
    sex="M"
))

print(f"Assigned MS-DRG: {grouping_result.ms_drg}")

# Step 2: Calculate payment using assigned DRG
repricer = MedicareRepricer(data_directory=Path("data"))

claim = Claim(
    claim_id="INTEGRATED-001",
    lines=[ClaimLine(
        line_number=1,
        procedure_code="INPATIENT",
        place_of_service="21",
        locality="01",
        ms_drg_code=grouping_result.ms_drg,  # ← Use grouped DRG
        provider_number="100001",
        total_charges=95000.00,
        covered_days=7
    )]
)

repriced = repricer.reprice_claim(claim)
payment = repriced.lines[0]

print(f"Medicare Payment: ${payment.medicare_allowed:,.2f}")
```

---

## Extending the Grouper

The grouper is designed to be expandable. Here's how to add coverage:

### Adding New ICD-10 Diagnosis Codes

Edit `data/icd10_cm_data.json`:

```json
{
  "codes": {
    "MDC_05_CIRCULATORY_SYSTEM": {
      "I25.10": {
        "description": "Atherosclerotic heart disease of native coronary artery...",
        "mdc": "05",
        "is_cc": true,
        "is_mcc": false
      }
    }
  }
}
```

### Adding New ICD-10 Procedure Codes

Edit `data/icd10_pcs_data.json`:

```json
{
  "procedures": {
    "CARDIOVASCULAR_PROCEDURES": {
      "02703ZZ": {
        "description": "Dilation of coronary artery...",
        "is_or_procedure": false,
        "is_non_or_procedure": true
      }
    }
  }
}
```

### Adding New Grouping Rules

Edit `data/drg_grouping_rules.json`:

```json
{
  "grouping_rules": {
    "MDC_05_CIRCULATORY": {
      "surgical_drgs": {
        "new_procedure_family": {
          "procedure_pattern": "027.*",
          "description": "New procedure type",
          "drgs": {
            "with_mcc": "246",
            "with_cc": "247",
            "without_cc_mcc": "248"
          }
        }
      }
    }
  }
}
```

---

## Limitations

### Current Implementation Limitations

1. **ICD-10 Code Coverage**: Starter set covers common conditions; full implementation would include 70,000+ codes
2. **CC Exclusion Lists**: Basic exclusions implemented; full CMS exclusion lists not complete
3. **Pre-MDC Logic**: Framework present but not fully implemented for all transplant/ECMO cases
4. **MDC 24 & 25 Special Logic**: Multiple trauma and HIV special grouping rules simplified
5. **Age/Sex Edits**: Basic support; some age-specific DRG rules not implemented

### What This Grouper CAN Do ✅

- Assign MS-DRGs for most common inpatient scenarios
- Correctly identify CC/MCC presence
- Distinguish surgical vs. medical DRGs
- Handle 25 MDCs with appropriate organ system logic
- Integrate with IPPS pricer for payment calculation

### What Requires Expansion ⚠️

- Full ICD-10-CM/PCS code sets (ongoing data addition)
- Complete CC exclusion lists per principal diagnosis
- All 998 MS-DRG grouping rules (currently covers major families)
- Present on Admission (POA) indicator logic
- Age-specific DRG variants (neonatal, pediatric)

---

## Example Use Cases

### Use Case 1: Quality Assurance

Validate that hospital-assigned DRGs match expected groupings:

```python
# Hospital claims data includes assigned DRG
hospital_assigned_drg = "470"

# Use grouper to verify
result = grouper.assign_drg(GrouperInput(
    principal_diagnosis="M16.11",
    procedures=["0SR9019"],
    age=72,
    sex="F"
))

if result.ms_drg != hospital_assigned_drg:
    print(f"DRG mismatch: Hospital={hospital_assigned_drg}, Expected={result.ms_drg}")
```

### Use Case 2: Claims Repricing

Convert claims with diagnosis/procedure codes to priced claims:

```python
# Raw claim data
raw_claim = {
    "principal_dx": "A41.9",
    "secondary_dx": ["R65.20", "N17.9"],
    "age": 82,
    "sex": "M",
    "provider": "100001",
    "charges": 125000
}

# Group to MS-DRG
grouping = grouper.assign_drg(GrouperInput(
    principal_diagnosis=raw_claim["principal_dx"],
    secondary_diagnoses=raw_claim["secondary_dx"],
    age=raw_claim["age"],
    sex=raw_claim["sex"]
))

# Price using assigned DRG
# ... (use MedicareRepricer as shown earlier)
```

### Use Case 3: Predictive Analytics

Analyze expected payments for planned procedures:

```python
# Planned hip replacement
planned_drg = grouper.assign_drg(GrouperInput(
    principal_diagnosis="M16.11",
    procedures=["0SR9019"],
    age=70,
    sex="F"
))

print(f"Expected DRG: {planned_drg.ms_drg}")
print(f"Expected LOS: {planned_drg.geometric_mean_los} days")
print(f"Relative Weight: {planned_drg.relative_weight}")

# Estimate payment
estimated_payment = planned_drg.relative_weight * base_rate  # Base rate from IPPS pricer
```

---

## Testing

Run the test suite:

```bash
pytest test_grouper.py -v
```

Run examples:

```bash
python examples/grouper_example.py
```

---

## Version Information

- **Grouper Version**: 43.0 (FY 2026)
- **ICD-10-CM Version**: FY 2026
- **ICD-10-PCS Version**: FY 2026
- **MS-DRG Version**: V43 (October 2025 - September 2026)

---

## References

- [CMS MS-DRG Classifications and Software](https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps/ms-drg-classifications-and-software)
- [ICD-10-CM/PCS MS-DRG v43.0 Definitions Manual](https://www.cms.gov/icd10m/FY2026-fr-v43-fullcode-cms/)
- [IPPS Final Rule FY 2026](https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps)

---

## Support

For questions or issues with the grouper:

1. Check the examples in `examples/grouper_example.py`
2. Review test cases in `test_grouper.py`
3. Consult this documentation
4. File an issue on the project repository

---

**Last Updated**: November 2025
**Author**: Medicare-Repricer Project
