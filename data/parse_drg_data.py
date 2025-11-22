#!/usr/bin/env python3
"""
Parse MS-DRG data from CMS MDC text files and create a complete JSON file
with estimated weights and length of stay values.
"""

import json
import re
from pathlib import Path
from typing import Dict, List

def parse_mdcs_files(data_dir: Path) -> Dict[str, str]:
    """Parse all MDC text files and extract DRG codes and descriptions."""
    drg_data = {}

    # MDC files to process
    mdc_files = [
        "mdcs_00_07.txt",
        "mdcs_08_11.txt",
        "mdcs_12_21.txt",
        "mdcs_22_25.txt"
    ]

    # Pattern to match DRG definitions
    # Example: "DRG 001 HEART TRANSPLANT OR IMPLANT OF HEART ASSIST SYSTEM WITH MCC"
    drg_pattern = re.compile(r'^DRG\s+(\d{3})\s+(.+)$', re.IGNORECASE)

    for filename in mdc_files:
        filepath = data_dir / filename
        if not filepath.exists():
            print(f"Warning: {filename} not found, skipping...")
            continue

        print(f"Processing {filename}...")
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = drg_pattern.match(line.strip())
                if match:
                    drg_code = match.group(1)
                    description = match.group(2).strip()
                    # Clean up the description
                    description = ' '.join(description.split())
                    drg_data[drg_code] = description

    return drg_data

def estimate_drg_values(drg_code: str, description: str) -> Dict:
    """
    Estimate relative weight and LOS values based on DRG characteristics.
    These are rough estimates based on typical patterns.
    """
    desc_lower = description.lower()

    # Base values
    relative_weight = 1.0
    geometric_mean_los = 3.5
    arithmetic_mean_los = 4.5

    # Adjust based on severity indicators
    if 'with mcc' in desc_lower or 'with major' in desc_lower:
        relative_weight *= 1.5
        geometric_mean_los *= 1.3
        arithmetic_mean_los *= 1.3
    elif 'with cc' in desc_lower or 'with complication' in desc_lower:
        relative_weight *= 1.15
        geometric_mean_los *= 1.1
        arithmetic_mean_los *= 1.1
    elif 'without cc/mcc' in desc_lower or 'without mcc' in desc_lower:
        relative_weight *= 0.8
        geometric_mean_los *= 0.8
        arithmetic_mean_los *= 0.8

    # Adjust for procedure types
    if any(word in desc_lower for word in ['transplant', 'ecmo', 'tracheostomy']):
        relative_weight *= 3.5
        geometric_mean_los *= 2.5
        arithmetic_mean_los *= 2.5
    elif any(word in desc_lower for word in ['major joint', 'cardiac', 'craniotomy']):
        relative_weight *= 2.0
        geometric_mean_los *= 1.5
        arithmetic_mean_los *= 1.5
    elif any(word in desc_lower for word in ['surgical', 'procedure', 'operation']):
        relative_weight *= 1.3
        geometric_mean_los *= 1.2
        arithmetic_mean_los *= 1.2

    # Adjust for specific conditions
    if any(word in desc_lower for word in ['septicemia', 'sepsis', 'respiratory failure']):
        relative_weight *= 1.4
        geometric_mean_los *= 1.3
        arithmetic_mean_los *= 1.3
    elif any(word in desc_lower for word in ['rehabilitation', 'aftercare']):
        geometric_mean_los *= 2.0
        arithmetic_mean_los *= 2.0
    elif any(word in desc_lower for word in ['psychoses', 'mental']):
        geometric_mean_los *= 1.5
        arithmetic_mean_los *= 1.5

    # Adjust for newborn/neonate
    if any(word in desc_lower for word in ['newborn', 'neonate']):
        geometric_mean_los *= 0.5
        arithmetic_mean_los *= 0.5

    return {
        "ms_drg": drg_code,
        "description": description,
        "relative_weight": round(relative_weight, 4),
        "geometric_mean_los": round(geometric_mean_los, 1),
        "arithmetic_mean_los": round(arithmetic_mean_los, 1)
    }

def main():
    # Set up paths
    data_dir = Path(__file__).parent

    # Parse DRG data from MDC files
    print("Parsing MDC files...")
    drg_descriptions = parse_mdcs_files(data_dir)

    print(f"Found {len(drg_descriptions)} DRG codes from MDC files")

    # Create complete DRG list (001-998)
    complete_drg_list = []

    for drg_num in range(1, 999):
        drg_code = f"{drg_num:03d}"

        if drg_code in drg_descriptions:
            # Use parsed description
            description = drg_descriptions[drg_code]
            drg_entry = estimate_drg_values(drg_code, description)
        else:
            # Create placeholder for missing DRG codes
            drg_entry = {
                "ms_drg": drg_code,
                "description": f"MS-DRG {drg_code} - Reserved/Not Currently Used",
                "relative_weight": 1.0,
                "geometric_mean_los": 3.5,
                "arithmetic_mean_los": 4.5
            }

        complete_drg_list.append(drg_entry)

    # Save to JSON
    output_file = data_dir / "ms_drg_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_drg_list, f, indent=2)

    print(f"Complete DRG data saved to {output_file}")
    print(f"Total DRG codes: {len(complete_drg_list)}")
    print(f"DRG codes with descriptions from CMS: {len(drg_descriptions)}")
    print(f"DRG codes marked as reserved: {998 - len(drg_descriptions)}")

if __name__ == "__main__":
    main()
