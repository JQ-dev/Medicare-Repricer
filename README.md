# Medicare Claims Repricing Interface

A functional Python interface for repricing healthcare claims to Medicare rates.

## Overview

This system reprices medical claims based on official Medicare fee schedules, including:
- Resource-Based Relative Value Scale (RBRVS) for physician services
- Geographic adjustment via GPCIs (Geographic Practice Cost Indices)
- Multiple procedure payment reduction (MPPR)
- Professional vs. Facility pricing

## Features

- **Procedure-based repricing**: Uses CPT/HCPCS codes with Medicare Physician Fee Schedule
- **Diagnosis code support**: ICD-10 codes for claim validation
- **Location-based adjustments**: Geographic Practice Cost Index (GPCI) by locality
- **Facility vs. Non-Facility pricing**: Automatic adjustment based on place of service
- **Multiple modifier support**: Professional component (26), Technical component (TC), and bilateral procedures (50)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from medicare_repricing import MedicareRepricer, Claim, ClaimLine

# Initialize the repricer
repricer = MedicareRepricer()

# Create a claim with diagnostic and procedure codes
claim = Claim(
    claim_id="CLM001",
    patient_id="PAT001",
    diagnosis_codes=["I10", "E11.9"],  # Essential hypertension, Type 2 diabetes
    lines=[
        ClaimLine(
            line_number=1,
            procedure_code="99213",  # Office visit, established patient
            modifier=None,
            place_of_service="11",  # Office
            locality="01",  # Manhattan, NY
            units=1
        ),
        ClaimLine(
            line_number=2,
            procedure_code="80053",  # Comprehensive metabolic panel
            modifier=None,
            place_of_service="11",
            locality="01",
            units=1
        )
    ]
)

# Reprice the claim
repriced_claim = repricer.reprice_claim(claim)

# View results
print(f"Total Medicare Allowed: ${repriced_claim.total_allowed:.2f}")
for line in repriced_claim.lines:
    print(f"Line {line.line_number}: {line.procedure_code} = ${line.medicare_allowed:.2f}")
```

## Data Models

### Claim Structure
- `claim_id`: Unique claim identifier
- `patient_id`: Patient identifier
- `diagnosis_codes`: List of ICD-10 diagnosis codes
- `lines`: List of ClaimLine objects

### ClaimLine Structure
- `line_number`: Sequential line number
- `procedure_code`: CPT or HCPCS procedure code
- `modifier`: Optional procedure modifier (26, TC, 50, etc.)
- `place_of_service`: Two-digit POS code (11=Office, 22=Outpatient Hospital, etc.)
- `locality`: Medicare locality code for GPCI
- `units`: Number of units

## Medicare Calculation Methodology

The system uses the standard Medicare Physician Fee Schedule formula:

```
Payment = (Work RVU × Work GPCI + Practice Expense RVU × PE GPCI + Malpractice RVU × MP GPCI) × Conversion Factor
```

Where:
- **RVU** = Relative Value Unit (work, practice expense, malpractice)
- **GPCI** = Geographic Practice Cost Index
- **Conversion Factor** = Annual Medicare conversion factor (currently ~$33.29 for 2024)

## License

MIT License
