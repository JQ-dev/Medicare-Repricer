# Medicare Fee Schedule 2025 Update

## Summary

Updated the Medicare Repricer to use the 2025 Medicare Physician Fee Schedule (PFS) data with the official 2025 conversion factor and provided tools to download and integrate the complete CMS dataset.

## Changes Made

### 1. Updated Conversion Factor (fee_schedule.py)

**Updated**: `medicare_repricing/fee_schedule.py`

- Changed default conversion factor from $33.2875 (2024) to **$32.35 (2025)**
- Updated in both `MedicareFeeSchedule.__init__()` and `create_default_fee_schedule()`
- Added documentation noting the historical conversion factors

**Impact**: All repricing calculations now use the official 2025 Medicare conversion factor, resulting in a 2.83% decrease in payment amounts compared to 2024.

### 2. Created CMS Data Download Script

**New file**: `scripts/download_cms_data.py`

A comprehensive Python script to download and parse official CMS fee schedule data:

**Features**:
- Downloads RVU (Relative Value Unit) data from CMS
- Downloads GPCI (Geographic Practice Cost Index) data
- Parses Excel/CSV files from CMS
- Converts data to JSON format compatible with the repricing system
- Handles various CMS file formats and column naming conventions
- Provides fallback to default GPCI data if file not available

**Usage**:
```bash
# Manual download approach (recommended due to CMS website restrictions)
python scripts/download_cms_data.py --rvu-file /path/to/PPRRVU25.xlsx --output-dir ./data
```

**Requirements** (in `requirements-data.txt`):
- pandas >= 2.0.0
- openpyxl >= 3.1.0
- requests >= 2.31.0
- beautifulsoup4 >= 4.12.0

### 3. Created Data Directory Structure

**New directory**: `data/`

This directory will contain the official CMS fee schedule data in JSON format:
- `rvu_data.json` - Complete RVU data for all CPT/HCPCS codes
- `gpci_data.json` - GPCI adjustment factors for all Medicare localities

### 4. Comprehensive Documentation

**New file**: `data/README.md`

Detailed documentation including:
- Instructions for downloading CMS data files
- File format specifications
- Usage examples
- Links to official CMS resources
- Troubleshooting guide

### 5. Dependencies File

**New file**: `requirements-data.txt`

Separate requirements file for data download/processing tools, keeping them isolated from core application dependencies.

## 2025 Medicare Fee Schedule Key Facts

### Official Information
- **Conversion Factor**: $32.35 (down from $33.2875 in 2024)
- **Decrease**: -$0.94 (-2.83%)
- **Effective Date**: January 1, 2025
- **Final Rule**: CMS-1807-F
- **Published**: November 1, 2024

### Important Changes
1. **Work GPCI Floor Expired**: The 1.0 Work GPCI floor that was in effect through 2023 has expired
2. **Updated RVU Values**: Various procedures have updated RVU values for 2025
3. **New CPT Codes**: Addition of new procedure codes for 2025
4. **Quarterly Updates**: CMS releases quarterly updates (RVU25A, B, C, D)

## Data Sources

### Official CMS Resources
- **RVU Files**: https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a
- **PFS Home**: https://www.cms.gov/medicare/payment/fee-schedules/physician
- **Lookup Tool**: https://www.cms.gov/medicare/physician-fee-schedule/search
- **Documentation**: https://www.cms.gov/medicare/physician-fee-schedule/search/documentation

## How to Get Complete 2025 Data

### Step 1: Download from CMS

Visit the CMS website to download the official files:
```
https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a
```

Download:
- `RVU25A.ZIP` (contains `PPRRVU25.xlsx` or similar)
- GPCI data file (if available separately)

### Step 2: Process with Script

Run the processing script:
```bash
cd Medicare-Repricer
python scripts/download_cms_data.py --rvu-file /path/to/PPRRVU25.xlsx --output-dir ./data
```

### Step 3: Load in Application

The fee schedule will automatically load the data:
```python
from pathlib import Path
from medicare_repricing.fee_schedule import MedicareFeeSchedule

fee_schedule = MedicareFeeSchedule(conversion_factor=32.35)
fee_schedule.load_from_directory(Path("data"))
```

## Testing

All existing tests continue to pass with the 2025 conversion factor:

```bash
$ python test_repricing.py
============================== 14 passed ==============================
```

Test coverage includes:
- Basic repricing calculations
- Geographic adjustments
- Facility vs non-facility settings
- Modifier handling (26, 50, etc.)
- Multiple Procedure Payment Reduction (MPPR)
- Validation and error handling

## Backward Compatibility

The system remains backward compatible:
- Sample data still provided in `fee_schedule.py` for testing
- `create_default_fee_schedule()` function works without external data files
- Existing code continues to work without modifications
- Can specify different conversion factors for historical calculations

## File Changes Summary

```
Modified:
  medicare_repricing/fee_schedule.py

Created:
  scripts/download_cms_data.py
  data/README.md
  requirements-data.txt
  MEDICARE_2025_UPDATE.md (this file)

Created (empty directories):
  data/
  scripts/
```

## Next Steps

1. **Download CMS Data**: Follow the instructions in `data/README.md` to download the complete 2025 dataset
2. **Process Data**: Run the download script to convert CMS files to JSON format
3. **Update Applications**: Ensure any applications using this library are using the correct conversion factor
4. **Quarterly Updates**: Check CMS website quarterly for updated RVU files (April, July, October releases)

## Notes

### Why Manual Download?

The CMS website blocks automated downloads (returns 403 Forbidden for programmatic access). Users must manually download the files from the CMS website, then use our parsing script to convert them to the required JSON format.

### Data Accuracy

Always verify critical calculations against official CMS sources. This is especially important for:
- High-value procedures
- Unusual modifiers
- New CPT codes
- Geographic areas with significant GPCI adjustments

### Support

For questions about:
- **CMS data**: Contact CMS or consult official documentation
- **This tool**: Refer to the project documentation and test cases

## References

1. CMS (2024). "Calendar Year (CY) 2025 Medicare Physician Fee Schedule Final Rule"
2. Federal Register. "Medicare and Medicaid Programs; CY 2025 Payment Policies Under the Physician Fee Schedule"
3. CMS Physician Fee Schedule Relative Value Files: https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files

---

**Date**: November 19, 2025
**Version**: 2025.1
**Author**: Medicare Repricer Development Team
