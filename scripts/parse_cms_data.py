#!/usr/bin/env python3
"""
Parse actual CMS Medicare fee schedule data files and convert to JSON.

This script processes the PPRRVU2025_Oct.csv and GPCI2025.csv files from CMS
and converts them into the JSON format used by the Medicare repricing system.
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional


def parse_rvu_csv(csv_path: Path) -> List[Dict]:
    """
    Parse the CMS PPRRVU CSV file.

    Column positions (0-indexed):
    0: HCPCS
    1: MOD (Modifier)
    2: DESCRIPTION
    3: STATUS CODE
    5: WORK RVU
    6: NON-FAC PE RVU
    8: FACILITY PE RVU
    10: MP RVU
    18: MULT PROC

    Args:
        csv_path: Path to PPRRVU2025_Oct.csv file

    Returns:
        List of RVU data dictionaries
    """
    rvu_data = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header lines until we find the data
        for _ in range(10):  # Skip the first 10 lines (headers)
            next(f)

        reader = csv.reader(f)

        for row in reader:
            try:
                if len(row) < 19:  # Need at least 19 columns
                    continue

                # Extract basic info
                procedure_code = row[0].strip()
                if not procedure_code:
                    continue

                # Skip if status code indicates not payable
                status_code = row[3].strip() if len(row) > 3 else ''
                if status_code not in ['A', 'R', 'T']:
                    continue  # Only include active, restricted, or injection codes

                modifier = row[1].strip() if row[1].strip() else None
                description = row[2].strip()

                # Parse RVU values
                def safe_float(value: str, default: float = 0.0) -> float:
                    try:
                        val = value.strip()
                        return float(val) if val and val.upper() != 'NA' else default
                    except (ValueError, AttributeError):
                        return default

                work_rvu = safe_float(row[5])
                pe_rvu_nf = safe_float(row[6])
                pe_rvu_f = safe_float(row[8])
                mp_rvu = safe_float(row[10])

                # Parse multiple procedure indicator
                mult_proc = row[18].strip() if len(row) > 18 else '0'
                try:
                    mp_indicator = int(mult_proc) if mult_proc.isdigit() else 0
                except:
                    mp_indicator = 0

                # Create RVU entry
                rvu_entry = {
                    'procedure_code': procedure_code,
                    'modifier': modifier,
                    'description': description[:200],  # Truncate long descriptions
                    'work_rvu_nf': work_rvu,
                    'pe_rvu_nf': pe_rvu_nf,
                    'mp_rvu_nf': mp_rvu,
                    'work_rvu_f': work_rvu,
                    'pe_rvu_f': pe_rvu_f,
                    'mp_rvu_f': mp_rvu,
                    'mp_indicator': mp_indicator
                }

                rvu_data.append(rvu_entry)

            except Exception as e:
                print(f"Warning: Error parsing row: {e}", file=sys.stderr)
                continue

    print(f"Parsed {len(rvu_data)} RVU entries", file=sys.stderr)
    return rvu_data


def parse_gpci_csv(csv_path: Path) -> List[Dict]:
    """
    Parse the CMS GPCI CSV file.

    Args:
        csv_path: Path to GPCI2025.csv file

    Returns:
        List of GPCI data dictionaries
    """
    gpci_data = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header lines
        next(f)  # Title line
        next(f)  # Blank line

        reader = csv.DictReader(f)

        for row in reader:
            try:
                locality = row['Locality Number'].strip()
                locality_name = row['Locality Name'].strip()

                # Parse GPCI values
                def safe_float(value: str, default: float = 1.0) -> float:
                    try:
                        return float(value.strip())
                    except (ValueError, AttributeError):
                        return default

                work_gpci = safe_float(row.get('2025 PW GPCI (with 1.0 Floor)', '1.0'))
                pe_gpci = safe_float(row.get('2025 PE GPCI', '1.0'))
                mp_gpci = safe_float(row.get('2025 MP GPCI', '1.0'))

                gpci_entry = {
                    'locality': locality,
                    'locality_name': locality_name,
                    'work_gpci': work_gpci,
                    'pe_gpci': pe_gpci,
                    'mp_gpci': mp_gpci
                }

                gpci_data.append(gpci_entry)

            except Exception as e:
                print(f"Warning: Error parsing GPCI row: {e}", file=sys.stderr)
                continue

    print(f"Parsed {len(gpci_data)} GPCI entries", file=sys.stderr)
    return gpci_data


def main():
    """Main entry point."""
    # Get data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data' / 'ruv25d'
    output_dir = script_dir.parent / 'data'

    # Check if files exist
    rvu_file = data_dir / 'PPRRVU2025_Oct.csv'
    gpci_file = data_dir / 'GPCI2025.csv'

    if not rvu_file.exists():
        print(f"Error: RVU file not found: {rvu_file}", file=sys.stderr)
        return 1

    if not gpci_file.exists():
        print(f"Error: GPCI file not found: {gpci_file}", file=sys.stderr)
        return 1

    print(f"Parsing RVU data from {rvu_file}...")
    rvu_data = parse_rvu_csv(rvu_file)

    print(f"Parsing GPCI data from {gpci_file}...")
    gpci_data = parse_gpci_csv(gpci_file)

    # Add default entries to GPCI if not present
    locality_codes = {g['locality'] for g in gpci_data}
    if '00' not in locality_codes:
        gpci_data.append({
            'locality': '00',
            'locality_name': 'National Average',
            'work_gpci': 1.0,
            'pe_gpci': 1.0,
            'mp_gpci': 1.0
        })
    if '99' not in locality_codes:
        gpci_data.append({
            'locality': '99',
            'locality_name': 'Default/Office',
            'work_gpci': 1.0,
            'pe_gpci': 1.0,
            'mp_gpci': 1.0
        })

    # Save to JSON files
    rvu_output = output_dir / 'rvu_data.json'
    gpci_output = output_dir / 'gpci_data.json'

    print(f"Writing RVU data to {rvu_output}...")
    with open(rvu_output, 'w') as f:
        json.dump(rvu_data, f, indent=2)

    print(f"Writing GPCI data to {gpci_output}...")
    with open(gpci_output, 'w') as f:
        json.dump(gpci_data, f, indent=2)

    print(f"\nSuccess!")
    print(f"  RVU entries: {len(rvu_data)}")
    print(f"  GPCI entries: {len(gpci_data)}")
    print(f"\nFiles saved to:")
    print(f"  {rvu_output}")
    print(f"  {gpci_output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
