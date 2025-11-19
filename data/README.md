# Medicare Fee Schedule Data

This directory contains the 2025 Medicare Physician Fee Schedule (PFS) data used for claims repricing.

## Data Files

The following files should be placed in this directory:

- **rvu_data.json** - Relative Value Unit (RVU) data for all CPT/HCPCS codes
- **gpci_data.json** - Geographic Practice Cost Index (GPCI) data for all Medicare localities

## 2025 Medicare Fee Schedule Information

### Key Details
- **Conversion Factor**: $32.35 (decreased from 2024's $33.2875)
- **Effective Date**: January 1, 2025
- **Source**: CMS Physician Fee Schedule Final Rule (CMS-1807-F)

### Changes from 2024
- Conversion factor decreased by $0.94 (2.83%)
- Work GPCI floor of 1.0 expired (was in effect through 2023)
- Updated RVU values for various procedures
- New and revised CPT codes for 2025

## Downloading Official CMS Data

### Option 1: Manual Download (Recommended)

1. **Visit the CMS RVU Files Page**:
   ```
   https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a
   ```

2. **Download the RVU25A ZIP file**
   - File name: `RVU25A.ZIP` or similar
   - Size: Approximately 4MB
   - Contains: `PPRRVU25.xlsx` or similar Excel file

3. **Download GPCI Data** (from the same page or documentation page):
   ```
   https://www.cms.gov/medicare/physician-fee-schedule/search/documentation
   ```

4. **Extract and Process the Files**:
   ```bash
   cd /path/to/Medicare-Repricer
   python scripts/download_cms_data.py --rvu-file /path/to/PPRRVU25.xlsx --gpci-file /path/to/GPCI25.xlsx
   ```

### Option 2: Using the Download Script

We provide a Python script to help parse the downloaded CMS files:

```bash
cd scripts
python download_cms_data.py --help
```

**Requirements**:
```bash
pip install pandas openpyxl requests beautifulsoup4
```

**Basic Usage**:
```bash
# After manually downloading the files
python download_cms_data.py --rvu-file /path/to/PPRRVU25.xlsx --output-dir ../data
```

## File Formats

### RVU Data (rvu_data.json)

JSON array of objects with the following structure:

```json
[
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
]
```

**Fields**:
- `procedure_code`: CPT or HCPCS code
- `modifier`: Optional modifier (e.g., "26", "TC", "59")
- `description`: Procedure description
- `work_rvu_nf`: Work RVU (Non-Facility)
- `pe_rvu_nf`: Practice Expense RVU (Non-Facility)
- `mp_rvu_nf`: Malpractice RVU (Non-Facility)
- `work_rvu_f`: Work RVU (Facility)
- `pe_rvu_f`: Practice Expense RVU (Facility)
- `mp_rvu_f`: Malpractice RVU (Facility)
- `mp_indicator`: Multiple Procedure Payment Reduction (0=none, 2=50% reduction)

### GPCI Data (gpci_data.json)

JSON array of objects with the following structure:

```json
[
  {
    "locality": "01",
    "locality_name": "Manhattan, NY",
    "work_gpci": 1.094,
    "pe_gpci": 1.385,
    "mp_gpci": 1.797
  }
]
```

**Fields**:
- `locality`: Medicare locality code
- `locality_name`: Locality description
- `work_gpci`: Work GPCI adjustment factor
- `pe_gpci`: Practice Expense GPCI adjustment factor
- `mp_gpci`: Malpractice GPCI adjustment factor

## Using the Data

### Loading in Python

```python
from pathlib import Path
from medicare_repricing.fee_schedule import MedicareFeeSchedule

# Create fee schedule with 2025 conversion factor
fee_schedule = MedicareFeeSchedule(conversion_factor=32.35)

# Load data from JSON files
data_dir = Path("data")
fee_schedule.load_from_directory(data_dir)

# Look up an RVU
rvu = fee_schedule.get_rvu("99213")
if rvu:
    print(f"CPT 99213: Work RVU = {rvu.work_rvu_nf}")

# Look up a GPCI
gpci = fee_schedule.get_gpci("01")  # Manhattan, NY
if gpci:
    print(f"Manhattan Work GPCI = {gpci.work_gpci}")
```

### Sample Data

If you don't have the full CMS dataset, you can use the sample data provided in `fee_schedule.py`:

```python
from medicare_repricing.fee_schedule import create_default_fee_schedule

fee_schedule = create_default_fee_schedule()
```

This creates a fee schedule with commonly used CPT codes for testing purposes.

## Data Sources and References

### Official CMS Resources

- **CMS Physician Fee Schedule Home**: https://www.cms.gov/medicare/payment/fee-schedules/physician
- **RVU Files**: https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files
- **PFS Lookup Tool**: https://www.cms.gov/medicare/physician-fee-schedule/search
- **2025 Final Rule**: https://www.cms.gov/medicare/payment/fee-schedules/physician/federal-regulation-notices/cms-1807-f

### Additional Resources

- **Federal Register Notice**: Search for "Medicare Physician Fee Schedule 2025"
- **CMS Fact Sheet**: https://www.cms.gov/newsroom/fact-sheets/calendar-year-cy-2025-medicare-physician-fee-schedule-final-rule

## Quarterly Updates

CMS releases quarterly updates to the fee schedule:

- **RVU25A** - January 2025 (Q1)
- **RVU25B** - April 2025 (Q2)
- **RVU25C** - July 2025 (Q3)
- **RVU25D** - October 2025 (Q4)

Check the CMS website periodically for updates and download the latest quarterly file.

## Notes

1. **Data Accuracy**: Always verify critical calculations against official CMS sources
2. **Updates**: The fee schedule is updated quarterly; check for the latest version
3. **Licensing**: CMS data is public domain and free to use
4. **File Size**: The complete RVU file contains ~10,000+ procedure codes

## Troubleshooting

### Issue: "File not found" errors

Make sure the JSON files are in this directory:
```bash
ls -la data/
# Should show: rvu_data.json, gpci_data.json
```

### Issue: "Empty data" warnings

Run the download script to populate the files:
```bash
python scripts/download_cms_data.py --rvu-file /path/to/downloaded/file.xlsx
```

### Issue: "Column not found" errors

The CMS file format may have changed. Check the actual column names in the Excel file and update the column mapping in `download_cms_data.py`.

## Support

For issues with:
- **CMS data files**: Contact CMS at https://www.cms.gov/medicare/contact-us
- **This repricing tool**: Open an issue in the project repository
