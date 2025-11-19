#!/usr/bin/env python3
"""
Download and parse CMS Medicare Physician Fee Schedule data for 2025.

This script downloads the official CMS RVU and GPCI data files and converts
them into JSON format for use with the Medicare repricing system.

CMS Data Sources:
- RVU File: https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a
- GPCI File: Available on the same CMS page

Usage:
    python download_cms_data.py --year 2025 --output-dir ../data

Requirements:
    pip install pandas openpyxl requests beautifulsoup4
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please install required packages:")
    print("  pip install pandas openpyxl requests beautifulsoup4")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CMSDataDownloader:
    """Download and parse CMS Medicare fee schedule data."""

    # CMS base URLs
    CMS_BASE_URL = "https://www.cms.gov"
    RVU_PAGE_URL = "https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu{year}a"

    def __init__(self, year: int = 2025, output_dir: Path = Path("../data")):
        """
        Initialize the downloader.

        Args:
            year: Medicare fee schedule year
            output_dir: Directory to save output files
        """
        self.year = year
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_file(self, url: str, filename: str) -> Optional[Path]:
        """
        Download a file from a URL.

        Args:
            url: URL to download from
            filename: Local filename to save to

        Returns:
            Path to downloaded file, or None if failed
        """
        filepath = self.output_dir / filename

        try:
            logger.info(f"Downloading {url}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Saved to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

    def parse_rvu_file(self, filepath: Path) -> List[Dict]:
        """
        Parse the CMS RVU Excel file.

        The RVU file contains columns like:
        - HCPCS Code
        - Mod (Modifier)
        - Description
        - Work RVU
        - Non-Facility PE RVU
        - Facility PE RVU
        - MP RVU
        - Multiple Procedure (MULT PROC)

        Args:
            filepath: Path to RVU file (Excel or CSV)

        Returns:
            List of RVU data dictionaries
        """
        logger.info(f"Parsing RVU file: {filepath}")

        try:
            # Try to read as Excel first
            if filepath.suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath)

            logger.info(f"Loaded {len(df)} rows from RVU file")
            logger.info(f"Columns: {df.columns.tolist()}")

            rvu_data = []

            # Map CMS column names to our format (adjust based on actual file)
            # Note: Actual column names may vary - check the file
            column_mapping = {
                'HCPCS': 'procedure_code',
                'CPT®/HCPCS': 'procedure_code',
                'HCPCS Code': 'procedure_code',
                'MOD': 'modifier',
                'Modifier': 'modifier',
                'Description': 'description',
                'DESCRIPTION': 'description',
                'Work RVU': 'work_rvu',
                'WORK RVU': 'work_rvu',
                'NON-FAC PE RVU': 'pe_rvu_nf',
                'Non-Facility PE RVU': 'pe_rvu_nf',
                'FACILITY PE RVU': 'pe_rvu_f',
                'Facility PE RVU': 'pe_rvu_f',
                'MP RVU': 'mp_rvu',
                'MALPRACTICE RVU': 'mp_rvu',
                'MULT PROC': 'mp_indicator',
                'Multiple Procedure': 'mp_indicator',
            }

            # Normalize column names
            df.columns = df.columns.str.strip()

            for _, row in df.iterrows():
                try:
                    # Extract values with fallbacks for different column names
                    procedure_code = None
                    for col in ['HCPCS', 'CPT®/HCPCS', 'HCPCS Code']:
                        if col in df.columns:
                            procedure_code = str(row[col]).strip()
                            break

                    if not procedure_code or pd.isna(procedure_code):
                        continue

                    # Extract other fields
                    modifier = row.get('MOD', row.get('Modifier', None))
                    if pd.isna(modifier):
                        modifier = None
                    else:
                        modifier = str(modifier).strip()

                    description = str(row.get('Description', row.get('DESCRIPTION', '')))

                    # RVU values
                    work_rvu = self._parse_float(row.get('Work RVU', row.get('WORK RVU', 0)))
                    pe_rvu_nf = self._parse_float(row.get('NON-FAC PE RVU', row.get('Non-Facility PE RVU', 0)))
                    pe_rvu_f = self._parse_float(row.get('FACILITY PE RVU', row.get('Facility PE RVU', 0)))
                    mp_rvu = self._parse_float(row.get('MP RVU', row.get('MALPRACTICE RVU', 0)))

                    # Multiple procedure indicator
                    mp_indicator = self._parse_int(row.get('MULT PROC', row.get('Multiple Procedure', 0)))

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
                    logger.warning(f"Error parsing row: {e}")
                    continue

            logger.info(f"Parsed {len(rvu_data)} RVU entries")
            return rvu_data

        except Exception as e:
            logger.error(f"Failed to parse RVU file: {e}")
            return []

    def parse_gpci_file(self, filepath: Path) -> List[Dict]:
        """
        Parse the CMS GPCI file.

        The GPCI file contains columns like:
        - Locality
        - Locality Name
        - Work GPCI
        - PE GPCI
        - MP GPCI

        Args:
            filepath: Path to GPCI file

        Returns:
            List of GPCI data dictionaries
        """
        logger.info(f"Parsing GPCI file: {filepath}")

        try:
            if filepath.suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath)

            logger.info(f"Loaded {len(df)} rows from GPCI file")
            logger.info(f"Columns: {df.columns.tolist()}")

            gpci_data = []

            # Normalize column names
            df.columns = df.columns.str.strip()

            for _, row in df.iterrows():
                try:
                    locality = str(row.get('Locality', row.get('LOCALITY', ''))).strip()
                    if not locality or pd.isna(locality):
                        continue

                    locality_name = str(row.get('Locality Name', row.get('LOCALITY NAME', '')))
                    work_gpci = self._parse_float(row.get('Work GPCI', row.get('WORK GPCI', 1.0)))
                    pe_gpci = self._parse_float(row.get('PE GPCI', row.get('Practice Expense GPCI', 1.0)))
                    mp_gpci = self._parse_float(row.get('MP GPCI', row.get('Malpractice GPCI', 1.0)))

                    gpci_entry = {
                        'locality': locality,
                        'locality_name': locality_name,
                        'work_gpci': work_gpci,
                        'pe_gpci': pe_gpci,
                        'mp_gpci': mp_gpci
                    }

                    gpci_data.append(gpci_entry)

                except Exception as e:
                    logger.warning(f"Error parsing GPCI row: {e}")
                    continue

            logger.info(f"Parsed {len(gpci_data)} GPCI entries")
            return gpci_data

        except Exception as e:
            logger.error(f"Failed to parse GPCI file: {e}")
            return []

    def _parse_float(self, value) -> float:
        """Parse a float value, handling various formats."""
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _parse_int(self, value) -> int:
        """Parse an integer value, handling various formats."""
        try:
            if pd.isna(value):
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def save_json(self, data: List[Dict], filename: str) -> Path:
        """
        Save data to JSON file.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data)} entries to {filepath}")
        return filepath

    def process_manual_files(self, rvu_file: Path, gpci_file: Optional[Path] = None):
        """
        Process manually downloaded CMS files.

        Use this if automatic download fails. Download files from:
        https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a

        Args:
            rvu_file: Path to downloaded RVU file
            gpci_file: Optional path to downloaded GPCI file
        """
        logger.info("Processing manually downloaded files...")

        # Parse RVU file
        if rvu_file.exists():
            rvu_data = self.parse_rvu_file(rvu_file)
            if rvu_data:
                self.save_json(rvu_data, 'rvu_data.json')
        else:
            logger.error(f"RVU file not found: {rvu_file}")

        # Parse GPCI file if provided
        if gpci_file and gpci_file.exists():
            gpci_data = self.parse_gpci_file(gpci_file)
            if gpci_data:
                self.save_json(gpci_data, 'gpci_data.json')
        else:
            logger.warning("GPCI file not provided or not found")
            logger.info("Generating default GPCI data...")
            self._generate_default_gpci()

    def _generate_default_gpci(self):
        """Generate default GPCI data for common localities."""
        default_gpci = [
            {'locality': '00', 'locality_name': 'National Average', 'work_gpci': 1.000, 'pe_gpci': 1.000, 'mp_gpci': 1.000},
            {'locality': '01', 'locality_name': 'Manhattan, NY', 'work_gpci': 1.094, 'pe_gpci': 1.385, 'mp_gpci': 1.797},
            {'locality': '03', 'locality_name': 'Miami, FL', 'work_gpci': 1.000, 'pe_gpci': 1.038, 'mp_gpci': 2.168},
            {'locality': '05', 'locality_name': 'Los Angeles, CA', 'work_gpci': 1.037, 'pe_gpci': 1.189, 'mp_gpci': 0.681},
            {'locality': '16', 'locality_name': 'Chicago, IL', 'work_gpci': 1.004, 'pe_gpci': 1.041, 'mp_gpci': 1.306},
            {'locality': '26', 'locality_name': 'Dallas, TX', 'work_gpci': 1.003, 'pe_gpci': 0.987, 'mp_gpci': 0.917},
            {'locality': '99', 'locality_name': 'Default/Office', 'work_gpci': 1.000, 'pe_gpci': 1.000, 'mp_gpci': 1.000},
        ]
        self.save_json(default_gpci, 'gpci_data.json')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download and parse CMS Medicare fee schedule data'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Medicare fee schedule year (default: 2025)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('../data'),
        help='Output directory for JSON files (default: ../data)'
    )
    parser.add_argument(
        '--rvu-file',
        type=Path,
        help='Path to manually downloaded RVU file (Excel or CSV)'
    )
    parser.add_argument(
        '--gpci-file',
        type=Path,
        help='Path to manually downloaded GPCI file (Excel or CSV)'
    )

    args = parser.parse_args()

    downloader = CMSDataDownloader(year=args.year, output_dir=args.output_dir)

    if args.rvu_file:
        # Process manually downloaded files
        downloader.process_manual_files(args.rvu_file, args.gpci_file)
    else:
        # Provide instructions for manual download
        print("\n" + "="*70)
        print("MANUAL DOWNLOAD REQUIRED")
        print("="*70)
        print("\nThe CMS website blocks automated downloads.")
        print("Please manually download the 2025 Medicare fee schedule files:")
        print("\n1. Visit:")
        print("   https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu25a")
        print("\n2. Download the RVU25A ZIP file")
        print("   (Contains: PPRRVU25.xlsx or similar)")
        print("\n3. Extract the ZIP file")
        print("\n4. Run this script again with the file path:")
        print(f"   python {sys.argv[0]} --rvu-file /path/to/PPRRVU25.xlsx")
        print("\n5. Optionally, download GPCI data from the same page")
        print("   and provide it with --gpci-file")
        print("="*70)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
