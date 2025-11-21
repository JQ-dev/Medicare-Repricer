# Medicare Repricer Codebase Analysis

## Executive Summary

The Medicare Repricer is a Python application that reprices healthcare claims to Medicare rates using the official 2025 Medicare Physician Fee Schedule (PFS) data. The system is well-architected with clear separation of concerns and uses the standard Medicare RBRVS (Resource-Based Relative Value Scale) methodology.

**Current Status:**
- Supports ~10,087 procedure codes across all major CPT/HCPCS categories
- Uses official CMS 2025 data with $32.35 conversion factor
- Handles geographic adjustments (GPCI), facility vs. non-facility pricing, and modifiers
- Currently focused on physician services (professional claims)
- Has sample data for labs, imaging, anesthesia, and other services already loaded

---

## 1. CURRENT IMPLEMENTATION ARCHITECTURE

### 1.1 Core Components

**File Structure:**
```
Medicare-Repricer/
├── medicare_repricing/
│   ├── models.py              # Data models (Claim, ClaimLine, RepricedClaim)
│   ├── fee_schedule.py        # Fee schedule management (RVU, GPCI data)
│   ├── calculator.py          # Pricing calculation engine
│   ├── repricer.py            # Main orchestration interface
│   ├── zip_to_locality.py     # Zip code to Medicare locality mapping
│   └── __init__.py
├── data/
│   ├── rvu_data.json          # 10,087 procedure codes with RVU values
│   ├── gpci_data.json         # ~790 locality records with geographic adjustments
│   └── ruv25d/                # CMS source files (2025)
│       ├── PPRRVU2025_Oct.csv # Main RVU file
│       ├── ANES2025.csv       # Anesthesia data
│       ├── OPPSCAP_Oct.csv    # Hospital outpatient/ASC pricing
│       ├── GPCI2025.csv       # GPCI localities
│       └── 25LOCCO.csv        # Locality to state mapping
├── scripts/
│   ├── download_cms_data.py   # Data processing script
│   └── parse_cms_data.py      # CMS file parser
├── test_repricing.py          # Unit tests
├── example_usage.py           # Usage examples
└── test_repricer.ipynb        # Jupyter notebook demo
```

### 1.2 Key Classes

**1. Claim and ClaimLine Models (models.py)**
- `ClaimLine`: Represents a single line item
  - Required: `line_number`, `procedure_code`, `place_of_service`
  - Optional: `modifiers` (up to 2), `locality`, `zip_code`, `units`
  - Validates codes, modifiers, and place of service

- `Claim`: Container for claim lines
  - Required: `claim_id`, `lines` (min 1)

- `RepricedClaimLine` & `RepricedClaim`: Output models with detailed pricing components
  - Work RVU, PE RVU, MP RVU values
  - GPCI adjustments
  - Conversion factor
  - Medicare allowed amounts
  - Adjustment notes (for MPPR, modifiers, etc.)

**2. Fee Schedule (fee_schedule.py)**
- `RVUData`: Stores RVU values per procedure
  - Separate facility vs. non-facility RVU values
  - Work, Practice Expense (PE), Malpractice (MP) components
  - MPPR indicator (0=no reduction, 2=50% reduction)
  - Optional modifier support

- `GPCIData`: Geographic adjustment factors
  - Locality code and name
  - Work, PE, and MP GPCI values

- `MedicareFeeSchedule`: Manages all RVU and GPCI data
  - Load from JSON files or add programmatically
  - Supports modifier lookups
  - 2025 conversion factor: $32.35

**3. Calculator (calculator.py)**
```
Payment Formula:
Price = [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × CF

Where:
- CF = Conversion Factor ($32.35 for 2025)
- Facility/Non-Facility RVUs selected based on POS code
- MPPR (50%) applied to ranked multiple procedures
```

- `MedicareCalculator`: Implements payment formula
  - Determines facility vs. non-facility from place of service
  - Applies modifier adjustments sequentially
  - Implements MPPR (Multiple Procedure Payment Reduction)
  - Fallback to national average (locality "00") if locality not found

**4. Repricer (repricer.py)**
- `MedicareRepricer`: Main interface
  - Orchestrates claim repricing
  - Identifies MPPR procedures by RVU ranking
  - Maps zip codes to localities
  - Handles errors gracefully
  - Provides procedure and locality information queries

---

## 2. PRICING CALCULATION METHODOLOGY

### 2.1 Standard RBRVS Formula

The system implements the official Medicare Physician Fee Schedule formula:

```python
# Base payment (per unit, no MPPR)
base_payment = (
    (work_rvu * work_gpci) +
    (pe_rvu * pe_gpci) +
    (mp_rvu * mp_gpci)
) * conversion_factor

# With MPPR (if applicable)
if is_multiple_procedure and rank > 1 and has_mppr:
    payment = base_payment * 0.50  # 50% of base for 2nd+ procedures
else:
    payment = base_payment

# With units multiplier
final_allowed = payment * units
```

### 2.2 Place of Service Determination

**Facility vs. Non-Facility:**
- **Non-Facility** (higher PE RVU): Office (11), Home (12), Clinic (49), etc.
- **Facility** (lower PE RVU): Hospital (21-23), ASC (24), Inpatient Psych (51-56), etc.

```python
facility_pos_codes = {"21", "22", "23", "24", "26", "31", "34",
                     "51", "52", "53", "56", "61"}
```

### 2.3 Modifier Handling

Current supported modifiers:
- **26**: Professional component only (zeroes out PE RVU)
- **TC**: Technical component only (zeroes out Work and MP RVU)
- **50**: Bilateral procedure (150% payment)
- **52/53**: Reduced/discontinued services (50% reduction)
- **76/77**: Repeat procedure (full payment)
- **59/XE/XU/XP/XS**: Distinct procedural service (no adjustment)

Modifiers are applied **sequentially** if multiple are present.

### 2.4 Multiple Procedure Payment Reduction (MPPR)

- Applies 50% reduction to 2nd and subsequent procedures
- Based on MPPR indicator in RVU data (2 = subject to MPPR)
- Procedures ranked by total RVU value (highest to lowest)
- Highest-ranked procedure gets 100%, rest get 50%

---

## 3. SUPPORTED SERVICE TYPES & CODES

### 3.1 Service Categories Currently in Data

The system includes **10,087 procedure codes** covering all major service types:

| Category | Code Range | Count | Examples |
|----------|-----------|-------|----------|
| Urinary/Renal | 70xxx-79xxx | 1,681 | Renal imaging, cystoscopy |
| Musculoskeletal/Ortho | 20xxx-29xxx | 1,620 | Joint injections, fracture treatment |
| Medicine | 90xxx-99xxx | 1,308 | Office visits, preventive services |
| ENT | 30xxx-39xxx | 1,121 | Otoscopy, sinus procedures |
| Digestive | 60xxx-69xxx | 926 | Endoscopy, colonoscopy |
| Dental (D-codes) | D0000-D9999 | 920 | Dental procedures |
| Respiratory | 40xxx-49xxx | 854 | Bronchoscopy, pulmonary tests |
| Cardiovascular | 50xxx-59xxx | 778 | Cardiac catheterization, stents |
| General Surgery | 10xxx-19xxx | 418 | Biopsies, tissue repairs |
| HCPCS (G-codes) | G0000-G9999 | 237 | Preventive, screening services |
| Lab/Pathology | 80xxx-89xxx | 209 | Blood work, tissue analysis |
| Other | Various | 15 | Miscellaneous codes |

### 3.2 Currently Explicitly Supported

✓ **Office Visits** (99201-99215): All levels, new & established patients
✓ **Laboratory** (80xxx-89xxx): 209 codes for blood work, panels, tests
✓ **Imaging** (71xxx, 73xxx, etc.): X-rays, ultrasound, CT, MRI with 26/TC modifiers
✓ **Procedures**: Surgery, repairs, injections, biopsies, etc.
✓ **Modifiers**: Professional (26), Technical (TC), Bilateral (50), etc.
✓ **Geographic Adjustment**: GPCI by locality (~790 localities)
✓ **Facility vs. Non-Facility**: Different RVU values

### 3.3 Service Types in Data But Not Explicitly Featured

These are present in the RVU data but not documented/tested:

**Anesthesia Codes (00xxx-00xxx range)**
- Currently: ~11 codes in RVU data
- Available: ANES2025.csv in raw CMS data (different conversion factor)
- Status: Loaded as regular codes, but anesthesia-specific conversions not implemented

**DME/Orthotic/Prosthetic (E-codes, L-codes, K-codes)**
- Status: Present in RVU data
- Limitation: These typically don't use RVU-based pricing in Medicare; they use ASP (Average Selling Price) or flat fees

**Labs** (80xxx-89xxx range)
- Status: 209 codes loaded, fully functional
- RVU values present for all lab codes

**Dental** (D-codes)
- Status: 920 codes loaded
- Note: May have different MPPR rules than medical procedures

---

## 4. DATA STRUCTURE & LOADING

### 4.1 RVU Data Format

**File**: `data/rvu_data.json` (121,045 lines, ~10,087 procedure codes)

```json
{
  "procedure_code": "99213",
  "modifier": null,
  "description": "Office visit, established patient, moderate",
  "work_rvu_nf": 0.97,
  "pe_rvu_nf": 1.57,
  "mp_rvu_nf": 0.09,
  "work_rvu_f": 0.97,
  "pe_rvu_f": 1.18,
  "mp_rvu_f": 0.09,
  "mp_indicator": 0
}
```

**With Modifier**:
```json
{
  "procedure_code": "71046",
  "modifier": "26",
  "description": "Chest X-ray, 2 views - Professional",
  "work_rvu_nf": 0.22,
  "pe_rvu_nf": 0.00,
  "mp_rvu_nf": 0.19,
  "work_rvu_f": 0.22,
  "pe_rvu_f": 0.00,
  "mp_rvu_f": 0.19,
  "mp_indicator": 0
}
```

**Key Fields**:
- `nf` = Non-Facility (office, home, clinic)
- `f` = Facility (hospital, ASC)
- `mp_indicator`: 0 (no MPPR), 2 (50% MPPR applies)

### 4.2 GPCI Data Format

**File**: `data/gpci_data.json` (792 lines, ~790 unique localities)

```json
{
  "locality": "01",
  "locality_name": "ALASKA*",
  "work_gpci": 1.5,
  "pe_gpci": 1.081,
  "mp_gpci": 0.592
}
```

**Coverage**: All US states and territories with locality-specific adjustments

### 4.3 Data Loading Process

```python
# Automatic loading
repricer = MedicareRepricer(data_directory=Path("data"))
# Loads from data/rvu_data.json and data/gpci_data.json

# Or manual:
fee_schedule = MedicareFeeSchedule(conversion_factor=32.35)
fee_schedule.load_from_directory(Path("data"))
calculator = MedicareCalculator(fee_schedule)
```

### 4.4 CMS Source Files (in data/ruv25d/)

These are the official CMS files used to generate the JSON files:

1. **PPRRVU2025_Oct.csv** (2.5MB) - Main RVU file
   - All CPT/HCPCS codes with facility/non-facility RVUs
   - Imported from CMS quarterly releases (Oct = Q4 update)

2. **ANES2025.csv** (3.8KB) - Anesthesia data
   - Anesthesia conversion factor: $20.3178 (vs. PFS: $32.35)
   - Different pricing methodology

3. **OPPSCAP_Oct.csv** (544KB) - Hospital Outpatient/ASC pricing
   - Not currently integrated into repricer
   - Uses APC-based (Ambulatory Payment Classification) pricing, not RVU-based

4. **GPCI2025.csv** (5.2KB) - GPCI locality data
   - Imported directly to gpci_data.json

5. **25LOCCO.csv** (6.3KB) - Locality to state mapping
   - Used for zip code to locality mapping (partially)

---

## 5. CLAIMS PROCESSING FLOW

### 5.1 High-Level Flow

```
Input Claim
    ↓
[Validation]
    - Claim ID present
    - At least 1 line item
    - Unique line numbers
    ↓
[Locality Resolution]
    - If locality provided: use it
    - Else if zip_code: map to locality
    - Else: error
    ↓
[Identify MPPR Procedures]
    - Find all codes with MPPR indicator = 2
    - Rank by total RVU (highest → lowest)
    ↓
[For Each Line]
    - Lookup RVU by code and modifier
    - Lookup GPCI by locality
    - Select facility vs non-facility RVU
    - Apply modifier adjustments
    - Calculate: (RVU × GPCI) × CF
    - Apply MPPR if applicable (rank 2+)
    - Multiply by units
    ↓
[Aggregate & Return]
    - Total allowed = sum of all lines
    - Return detailed repriced claim
```

### 5.2 Error Handling

Current error handling is graceful:
- If procedure code not found: Creates repriced line with $0 allowed and error message
- If locality not found: Falls back to national average (locality "00")
- If zip code not mappable: Uses default, continues processing

---

## 6. WHAT'S CURRENTLY WORKING

### ✓ Implemented Features

1. **Basic Repricing**
   - CPT/HCPCS code lookup
   - RVU-based payment calculation
   - Geographic adjustments (GPCI)

2. **Place of Service**
   - Facility vs. non-facility RVU selection
   - ~15 facility settings recognized

3. **Modifiers**
   - Professional component (26)
   - Technical component (TC)
   - Bilateral (50)
   - Distinct procedural (59, XE, XU, XP, XS)
   - Reduced/discontinued (52, 53)
   - Repeat procedures (76, 77)

4. **Multiple Procedures**
   - MPPR (50%) applied correctly
   - Ranking by RVU value

5. **Data**
   - 10,087 CPT/HCPCS codes loaded
   - ~790 localities with GPCI
   - Zip code to locality mapping (sample)

6. **Testing**
   - 14 unit tests passing
   - Example scenarios covering all major features

---

## 7. WHAT'S NOT CURRENTLY SUPPORTED

### ✗ Missing/Limited Features

#### A. Anesthesia Services (00xxx range)

**Current State:**
- 11 anesthesia codes in RVU data
- Use same $32.35 conversion factor as PFS
- No special anesthesia handling

**What's Missing:**
- Anesthesia uses **different conversion factor**: $20.3178 (in ANES2025.csv)
- Anesthesia codes require **time-based unit reporting** (15-min blocks)
- No base unit + time unit calculation
- No code crosswalk for anesthesia (codes 00xxx map to surgical codes)

**CMS Data Available:**
- ANES2025.csv contains anesthesia conversions by locality
- Would need to parse and integrate separately

#### B. DME (Durable Medical Equipment)

**Current State:**
- ~70 DME codes in RVU data
- Treated like regular RVU-based codes

**What's Missing:**
- Medicare DME doesn't use RVU-based pricing
- Uses **ASP (Average Selling Price)** or **fee schedules**
- Different pricing by **rental vs. purchase**
- **CAPPED RENTAL** rules (e.g., 13 months then ownership)
- **Monthly payment amounts** per locality
- Requires separate DME fee schedule, not RVU-based

**Data Not Currently Available:**
- DME ASP/fee schedule data not in system
- Need separate DMEPOS fee schedule from CMS

#### C. Lab Services (80xxx-89xxx range)

**Current State:**
- 209 lab codes successfully loaded
- Pricing works with RVU-based system
- Some labs have $0 work RVU (technician-only services)

**What's Partially Working:**
- Most common labs (CBC, metabolic panel, TSH) work fine
- Complex lab bundles may not calculate correctly
- Some specialty labs may have incorrect RVUs

**What's Missing:**
- **Lab bundling rules**: CMS bundles certain lab combinations
- **Waived tests**: Some tests don't require reimbursement validation
- **Frequency limitations**: Some labs limited to certain frequencies
- **CLIA certification validation**: Lab must be certified for tests
- **Panel vs. individual component** pricing

#### D. Hospital Outpatient/ASC Pricing (OPPS)

**Current State:**
- OPPSCAP_Oct.csv file present but not integrated
- Still using PFS (Physician Fee Schedule) pricing

**What's Missing:**
- **APC-based pricing** (Ambulatory Payment Classification), not RVU-based
- Uses **HCPCS code** → **APC** → **Payment amount** mapping
- **Packaging rules**: Some services bundled into primary procedure
- **Pass-through drugs**: Separate reimbursement for high-cost drugs
- **Complexity adjustments**: Different rates for routine vs. complex cases

#### E. Service Type Categorization

**Current State:**
- No explicit service type field
- Code ranges not standardized
- Implicit categorization in code prefixes only

**What's Missing:**
- Explicit `service_type` or `charge_type` field
- Categorization logic (identify anesthesia vs. lab vs. DME automatically)
- Different processing rules per category
- **Claim validation** rules per service type

#### F. Dental (D-codes)

**Current State:**
- 920 dental codes loaded
- No special handling

**What's Missing:**
- Dental has **different MPPR rules** than medical
- Dental **MPPR indicators** may differ
- Dental procedures may have **annual maximum** limitations
- **Predetermination requirements** for high-cost procedures

#### G. Advanced Modifiers

**Not Yet Supported:**
- **Laterality modifiers** (LT, RT): Left/Right distinction
- **HCPCS modifiers** beyond basic ones
- **Sequence of events** modifiers
- **Care team modifiers** (for team-based care)
- **Timing modifiers** for repeated services
- **Subseq-encounter modifiers**: Multiple encounters same day

---

## 8. DATA GAPS & KNOWN LIMITATIONS

### 8.1 Zip Code Mapping

**Current State:**
- Sample mapping for major metro areas (NYC, LA, Chicago, etc.)
- Only 3-digit prefix matching
- Falls back to national average ("00") if not found

**Limitation:**
- Only covers ~50 zip code prefixes
- Missing most of US coverage
- Should ideally map all 43,000+ zip codes

**Data Source Available:**
- CMS provides 25LOCCO.csv (locality to state)
- Would need full zip-to-locality database

### 8.2 Place of Service Codes

**Supported Count:** ~15 facility codes, ~400+ POS codes in use

**Limitation:**
- Only facility vs. non-facility distinction
- No specialized POS handling (e.g., licensed independent practitioner clinic)
- All non-facility treated identically

### 8.3 Modifier Validation

**Current State:**
- Accepts any 2-character modifier string
- Doesn't validate if modifier is valid for the code
- Doesn't check for **incompatible modifier combinations**

**Example Problems:**
- Could apply 26 (professional) to labs (which don't have tech component)
- Could apply 26 + TC together (mutually exclusive)
- No validation against CMS modifier rules

### 8.4 MPPR Rules

**Simplified Implementation:**
- Applies same 50% rule to all procedures
- Real Medicare MPPR has **complex rules** per code family:
  - Global surgical package procedures
  - Bundling rules
  - Same-day/same-specialty requirements
  - PCR (Post-operative Consultants) rules

---

## 9. ARCHITECTURE FOR ADDING NEW SERVICE TYPES

### 9.1 Required Components for Each Service Type

To add support for a new service type (e.g., Anesthesia, DME), you would need:

#### 1. **Data Model Extension**
```python
# Add service_type to ClaimLine
class ClaimLine(BaseModel):
    ...
    service_type: Optional[str]  # 'PFS', 'ANES', 'DME', 'OPPS', etc.
    # Type-specific fields if needed
    anesthesia_base_units: Optional[int] = None  # For anesthesia
    anesthesia_time_units: Optional[int] = None  # For anesthesia
```

#### 2. **Fee Schedule Extension**
```python
# New data structures for each type
@dataclass
class AnesthesiaRVUData:
    code: str
    base_value: float  # Base unit value
    conversion_factor: float
    # Locality-specific conversion factors

@dataclass
class DMEFeeData:
    hcpcs_code: str
    monthly_rental: float
    purchase_price: float
    
class ServiceTypeFeeSchedule:
    pfs_schedule: MedicareFeeSchedule
    anesthesia_schedule: AnesthesiaSchedule
    dme_schedule: DMESchedule
    opps_schedule: OPPSSchedule
```

#### 3. **Calculator Extension**
```python
class ServiceTypeCalculator:
    def calculate_pfs(self, ...): ...  # Existing
    def calculate_anesthesia(self, ...): ...  # New
    def calculate_dme(self, ...): ...  # New
    def calculate_opps(self, ...): ...  # New
    
    def calculate_allowed_amount(self, service_type, ...):
        if service_type == 'ANES':
            return self.calculate_anesthesia(...)
        elif service_type == 'DME':
            return self.calculate_dme(...)
```

#### 4. **Data Source Integration**
```python
# For each new type, need:
# - Parser for CMS data file
# - JSON data loader
# - Validation rules

class AnesthesiaDataLoader:
    def load_from_csv(file_path):
        # Parse ANES2025.csv
        # Convert to internal format
        
class DMEDataLoader:
    def load_from_csv(file_path):
        # Parse CMS DME fee schedule
```

#### 5. **Validation Rules**
```python
class ServiceTypeValidator:
    @staticmethod
    def validate_anesthesia_line(line):
        # Validate base units and time units are present
        # Validate code is 00xxx range
        
    @staticmethod
    def validate_dme_line(line):
        # Validate rental vs. purchase specified
        # Validate locality present
```

### 9.2 Implementation Sequence

**Phase 1: Infrastructure** (enable service type routing)
1. Add `service_type` field to ClaimLine model
2. Create abstract `ServiceTypeCalculator` base class
3. Implement dispatcher in MedicareRepricer

**Phase 2: Anesthesia** (highest priority, uses similar RVU model)
1. Load ANES2025.csv data
2. Parse anesthesia conversion factors by locality
3. Implement anesthesia base+time unit calculation
4. Add anesthesia validation (base/time units required)

**Phase 3: DME** (significant changes needed)
1. Download/parse CMS DMEPOS fee schedule
2. Create separate DMECalculator (no RVU-based model)
3. Implement rental vs. purchase logic
4. Add CAPPED RENTAL rules

**Phase 4: Hospital Outpatient (OPPS)** (complex)
1. Load OPPSCAP_Oct.csv
2. Create APC lookup logic
3. Implement packaging rules
4. Add status indicator processing

**Phase 5: Advanced Features**
1. Lab bundling rules
2. Dental-specific MPPR
3. Laterality modifiers
4. Full zip code mapping

---

## 10. ADDING SPECIFIC SERVICE TYPE: ANESTHESIA EXAMPLE

### Step-by-Step Implementation

**Step 1: Update Models**
```python
# models.py
class ClaimLine(BaseModel):
    # ... existing fields ...
    service_type: Optional[str] = Field(None, description="PFS, ANES, DME, etc")
    anesthesia_base_units: Optional[int] = Field(None, description="Anesthesia base units")
    anesthesia_time_minutes: Optional[int] = Field(None, description="Anesthesia time in minutes")
```

**Step 2: Create Anesthesia Fee Schedule**
```python
# fee_schedule.py
@dataclass
class AnesthesiaConversionFactor:
    locality: str
    cf: float  # e.g., $20.3178
    
class AnesthesiaFeeSchedule:
    def __init__(self):
        self.conversion_factors: Dict[str, float] = {}
    
    def load_from_csv(self, filepath):
        with open(filepath) as f:
            for row in csv.DictReader(f):
                self.conversion_factors[row['Locality']] = float(row['Conversion Factor'])
    
    def get_cf(self, locality: str) -> float:
        return self.conversion_factors.get(locality, 20.3178)
```

**Step 3: Implement Anesthesia Calculation**
```python
# calculator.py
class AnesthesiaCalculator:
    def __init__(self, anesthesia_schedule: AnesthesiaFeeSchedule):
        self.anesthesia_schedule = anesthesia_schedule
    
    def calculate_anesthesia(self, code: str, base_units: int, 
                            time_minutes: int, locality: str) -> float:
        # Get base unit value for code (lookup from CMS crosswalk)
        base_unit_value = self.get_anesthesia_base_value(code)
        
        # Calculate time units (15-min = 1 unit, rounded up)
        time_units = (time_minutes + 14) // 15
        
        # Get conversion factor for locality
        cf = self.anesthesia_schedule.get_cf(locality)
        
        # Payment = (base_units + time_units) × base_unit_value × CF
        total_units = base_units + time_units
        return total_units * base_unit_value * cf
```

**Step 4: Integrate into Repricer**
```python
# repricer.py
class MedicareRepricer:
    def __init__(self, ...):
        # ... existing code ...
        self.anesthesia_calc = AnesthesiaCalculator(anesthesia_schedule)
    
    def reprice_claim(self, claim: Claim):
        for line in claim.lines:
            if line.service_type == 'ANES':
                allowed, details = self.anesthesia_calc.calculate_anesthesia(
                    line.procedure_code,
                    line.anesthesia_base_units,
                    line.anesthesia_time_minutes,
                    locality
                )
            else:
                # Existing PFS calculation
                allowed, details = self.calculator.calculate_allowed_amount(...)
```

---

## 11. SUPPORTING MULTIPLE PROCEDURE CATEGORIES

### 11.1 Service Type Aware Routing

```python
# Proposed architecture
class MedicareCalculatorFactory:
    calculators = {
        'PFS': MedicareCalculator,        # Physician Fee Schedule
        'ANES': AnesthesiaCalculator,     # Anesthesia
        'DME': DMECalculator,              # Durable Medical Equipment
        'OPPS': OPPSCalculator,            # Outpatient Prospective Payment
        'LAB': LabCalculator,              # Lab specific rules
        'DENTAL': DentalCalculator,        # Dental (different MPPR)
    }
    
    @staticmethod
    def get_calculator(service_type: str):
        return MedicareCalculatorFactory.calculators.get(service_type)

# Usage:
service_type = determine_service_type(procedure_code)  # From code prefix
calculator = MedicareCalculatorFactory.get_calculator(service_type)
allowed, details = calculator.calculate(line, fee_schedule)
```

### 11.2 Automatic Service Type Detection

```python
def determine_service_type(procedure_code: str) -> str:
    """Auto-detect service type from code prefix."""
    if procedure_code.startswith(('00', '01')):
        return 'ANES'
    elif procedure_code.startswith(('80', '81', '82', '83', '84', '85', '86', '87', '88', '89')):
        return 'LAB'
    elif procedure_code.startswith(('D', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9')):
        return 'DENTAL'
    elif procedure_code.startswith(('E', 'J', 'K', 'L', 'V5', 'V7')):
        return 'DME'
    elif procedure_code.startswith(('L', 'L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9')):
        return 'DME'
    else:
        return 'PFS'  # Default to Physician Fee Schedule
```

---

## 12. CMS DATA SOURCES & AVAILABILITY

### 12.1 Available in System

- ✓ **PPRRVU2025_Oct.csv** - Main RVU file (10,087 codes)
- ✓ **GPCI2025.csv** - Geographic adjustments (~790 localities)
- ✓ **ANES2025.csv** - Anesthesia conversion factors
- ✓ **OPPSCAP_Oct.csv** - Hospital outpatient pricing
- ✓ **25LOCCO.csv** - Locality reference

### 12.2 Available But Not Integrated

- **DME Fee Schedule** - CMS publishes separately
  - URL: cms.gov/dmepos
  - Format: Excel or CSV
  - Updates: Quarterly

- **Hospital Inpatient (DRG)** - Not applicable for claims repricing
  - Uses DRG system, not RVU-based

### 12.3 Data Processing Scripts

**Current:**
- `scripts/download_cms_data.py` - Parsing script provided

**Needed for Extensions:**
- Anesthesia CSV parser (ANES2025.csv → JSON)
- DME schedule parser
- OPPS APC parser
- Full zip code mapper

---

## 13. SUMMARY: ROADMAP FOR EXPANSION

### Immediate (< 1 week)
- [ ] Add `service_type` field to ClaimLine
- [ ] Implement auto-detection logic
- [ ] Create calculator dispatcher

### Short Term (1-4 weeks)
- [ ] Integrate anesthesia data (ANES2025.csv)
- [ ] Implement anesthesia calculation
- [ ] Add anesthesia tests
- [ ] Improve zip code mapping (full US coverage)

### Medium Term (1-2 months)
- [ ] DME fee schedule integration
- [ ] DME calculator (rental/purchase/capping logic)
- [ ] Hospital outpatient (OPPS) basic support
- [ ] Lab bundling rules

### Long Term (2-6 months)
- [ ] Advanced MPPR rules per code family
- [ ] Modifier validation against code
- [ ] Lateral/bilateral distinction modifiers
- [ ] Predetermination logic for high-value services
- [ ] Complete dental module
- [ ] Full CMS integration pipeline

### Infrastructure Improvements
- [ ] Unit test for each service type
- [ ] Example claims for each service type
- [ ] Service type detection test suite
- [ ] CMS data update automation
- [ ] Better error reporting per service type

---

## 14. TESTING & VALIDATION STRATEGY

### Current Tests (14 passing)
- Basic repricing
- Multiple lines
- Units multiplier
- Facility vs. non-facility
- Modifiers (26, 50)
- MPPR
- Geographic variation
- Zip code mapping
- Error handling

### Needed Tests for Extensions

```python
# Anesthesia tests
def test_anesthesia_base_units(): ...
def test_anesthesia_time_units(): ...
def test_anesthesia_conversion_factor(): ...

# DME tests
def test_dme_monthly_rental(): ...
def test_dme_purchase_price(): ...
def test_dme_capped_rental(): ...

# OPPS tests
def test_opps_apc_lookup(): ...
def test_opps_packaging(): ...

# Lab tests
def test_lab_bundling(): ...
def test_lab_frequency_limits(): ...
```

---

## 15. KEY TAKEAWAYS

1. **Current System**: Well-designed, clean architecture focused on PFS (physician fee schedule) pricing
2. **Strong Foundation**: 10,087 codes loaded, GPCI adjustments working, modifiers implemented
3. **Ready for Labs**: Lab codes already working, just need bundling rules
4. **Anesthesia Ready**: Data available (ANES2025.csv), moderate effort to integrate
5. **DME Complex**: Requires different pricing model, more substantial changes
6. **OPPS Different**: Hospital outpatient uses APC system, not RVU-based
7. **Architecture Scalable**: Can add new service types without breaking existing code
8. **Data Available**: All CMS source files present, just need parsing/integration

---

**Generated**: Analysis based on codebase exploration
**Version**: Medicare Repricer v2025.1
**Data**: 2025 Medicare Physician Fee Schedule
**Coverage**: 10,087 procedure codes across all major service categories

