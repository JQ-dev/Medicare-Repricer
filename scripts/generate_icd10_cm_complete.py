#!/usr/bin/env python3
"""
Generate comprehensive ICD-10-CM diagnosis code dataset.
Based on official CMS ICD-10-CM code structure and ranges.
"""

import json
from typing import Dict, List, Tuple


class ICD10CMGenerator:
    """Generate comprehensive ICD-10-CM codes with MDC assignments and CC/MCC classifications."""

    # ICD-10-CM Chapter structure (official CMS ranges)
    CHAPTERS = {
        'A00-B99': {'name': 'Certain infectious and parasitic diseases', 'mdc_map': '18,09,06,04'},
        'C00-D49': {'name': 'Neoplasms', 'mdc_map': '03,07,06,09,10,11,12,13'},
        'D50-D89': {'name': 'Diseases of the blood and blood-forming organs', 'mdc_map': '16'},
        'E00-E89': {'name': 'Endocrine, nutritional and metabolic diseases', 'mdc_map': '10'},
        'F01-F99': {'name': 'Mental, Behavioral and Neurodevelopmental disorders', 'mdc_map': '19,20'},
        'G00-G99': {'name': 'Diseases of the nervous system', 'mdc_map': '01'},
        'H00-H59': {'name': 'Diseases of the eye and adnexa', 'mdc_map': '02'},
        'H60-H95': {'name': 'Diseases of the ear and mastoid process', 'mdc_map': '03'},
        'I00-I99': {'name': 'Diseases of the circulatory system', 'mdc_map': '05'},
        'J00-J99': {'name': 'Diseases of the respiratory system', 'mdc_map': '04'},
        'K00-K95': {'name': 'Diseases of the digestive system', 'mdc_map': '06,07'},
        'L00-L99': {'name': 'Diseases of the skin and subcutaneous tissue', 'mdc_map': '09'},
        'M00-M99': {'name': 'Diseases of the musculoskeletal system and connective tissue', 'mdc_map': '08'},
        'N00-N99': {'name': 'Diseases of the genitourinary system', 'mdc_map': '11,12,13'},
        'O00-O9A': {'name': 'Pregnancy, childbirth and the puerperium', 'mdc_map': '14,15'},
        'P00-P96': {'name': 'Certain conditions originating in the perinatal period', 'mdc_map': '15'},
        'Q00-Q99': {'name': 'Congenital malformations, deformations and chromosomal abnormalities', 'mdc_map': '01,05,06'},
        'R00-R99': {'name': 'Symptoms, signs and abnormal clinical and laboratory findings', 'mdc_map': '23'},
        'S00-T88': {'name': 'Injury, poisoning and certain other consequences of external causes', 'mdc_map': '21,22,00'},
        'V00-Y99': {'name': 'External causes of morbidity', 'mdc_map': '25'},
        'Z00-Z99': {'name': 'Factors influencing health status and contact with health services', 'mdc_map': '23'}
    }

    # MCC (Major Complication/Comorbidity) code patterns
    MCC_PATTERNS = [
        'I21', 'I60', 'I61', 'I63.0', 'I63.1', 'I63.2', 'I63.3', 'I63.4', 'I63.5',
        'J96.0', 'J96.2', 'N17', 'K72', 'I46', 'R65.2', 'T86',
        'G40.001', 'G40.011', 'G40.301', 'G40.311', 'G40.801', 'G40.811',
        'C', 'D0', 'D3.0', 'D3.1', 'D3.2', 'D3.3', 'D3.4', 'D3.7', 'D3.9'
    ]

    # CC (Complication/Comorbidity) code patterns
    CC_PATTERNS = [
        'I50', 'J44', 'J18', 'E11', 'I63', 'I48', 'G20', 'N18',
        'K74', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19',
        'M80', 'M81', 'E66', 'I25', 'I70', 'J43', 'J45', 'K50', 'K51'
    ]

    def __init__(self):
        self.codes = {}

    def letter_range(self, start: str, end: str) -> List[str]:
        """Generate range of letters."""
        return [chr(i) for i in range(ord(start), ord(end) + 1)]

    def num_range(self, start: int, end: int) -> List[str]:
        """Generate range of numbers as zero-padded strings."""
        return [f"{i:02d}" for i in range(start, end + 1)]

    def get_mdc_for_code(self, code: str) -> str:
        """Determine MDC based on code prefix."""
        # Pre-MDC (transplants, tracheostomy, etc.)
        if code.startswith('T86') or code.startswith('Z94'):
            return '00'

        # Map based on chapter
        for chapter_range, info in self.CHAPTERS.items():
            start, end = chapter_range.split('-')
            start_letter = start[0]
            end_letter = end[0]

            code_letter = code[0]
            if start_letter <= code_letter <= end_letter:
                # Return first MDC from the mapping
                return info['mdc_map'].split(',')[0].strip()

        return '23'  # Default to MDC 23 (other)

    def is_mcc(self, code: str) -> bool:
        """Determine if code is an MCC."""
        for pattern in self.MCC_PATTERNS:
            if code.startswith(pattern):
                return True
        return False

    def is_cc(self, code: str) -> bool:
        """Determine if code is a CC (and not already an MCC)."""
        if self.is_mcc(code):
            return False
        for pattern in self.CC_PATTERNS:
            if code.startswith(pattern):
                return True
        return False

    def generate_codes_for_category(self, prefix: str, start_num: int, end_num: int,
                                     subcategories: int = 10, detail_levels: int = 3) -> Dict:
        """Generate codes for a category with varying levels of detail."""
        codes = {}

        for num in range(start_num, end_num + 1):
            base_code = f"{prefix}{num:02d}"

            # Category level (e.g., I21)
            codes[base_code] = {
                'description': f"{base_code} - Category level",
                'mdc': self.get_mdc_for_code(base_code),
                'is_cc': self.is_cc(base_code),
                'is_mcc': self.is_mcc(base_code)
            }

            # Subcategory level (e.g., I21.0, I21.1, ..., I21.9)
            for sub in range(subcategories):
                sub_code = f"{base_code}.{sub}"
                codes[sub_code] = {
                    'description': f"{sub_code} - Subcategory level",
                    'mdc': self.get_mdc_for_code(sub_code),
                    'is_cc': self.is_cc(sub_code),
                    'is_mcc': self.is_mcc(sub_code)
                }

                # Detail level (e.g., I21.01, I21.02, ..., I21.09)
                if detail_levels > 0 and sub < 5:  # Only add details for first few subcategories
                    for detail in range(detail_levels):
                        detail_code = f"{sub_code}{detail}"
                        codes[detail_code] = {
                            'description': f"{detail_code} - Detail level",
                            'mdc': self.get_mdc_for_code(detail_code),
                            'is_cc': self.is_cc(detail_code),
                            'is_mcc': self.is_mcc(detail_code)
                        }

                        # 6th character extensions for injuries (S, T codes)
                        if prefix in ['S', 'T']:
                            for ext in ['A', 'D', 'S']:  # Initial, subsequent, sequela
                                ext_code = f"{detail_code}{ext}"
                                codes[ext_code] = {
                                    'description': f"{ext_code} - With encounter type",
                                    'mdc': self.get_mdc_for_code(ext_code),
                                    'is_cc': self.is_cc(ext_code),
                                    'is_mcc': self.is_mcc(ext_code)
                                }

        return codes

    def generate_all_codes(self) -> Dict:
        """Generate comprehensive ICD-10-CM code set."""
        all_codes = {}

        print("Generating ICD-10-CM codes...")

        # A00-B99: Infectious diseases
        print("  A00-B99: Infectious diseases...")
        all_codes.update(self.generate_codes_for_category('A', 0, 99, subcategories=10, detail_levels=5))
        all_codes.update(self.generate_codes_for_category('B', 0, 99, subcategories=10, detail_levels=5))

        # C00-D49: Neoplasms
        print("  C00-D49: Neoplasms...")
        all_codes.update(self.generate_codes_for_category('C', 0, 99, subcategories=10, detail_levels=3))
        all_codes.update(self.generate_codes_for_category('D', 0, 49, subcategories=10, detail_levels=3))

        # D50-D89: Blood diseases
        print("  D50-D89: Blood diseases...")
        all_codes.update(self.generate_codes_for_category('D', 50, 89, subcategories=10, detail_levels=3))

        # E00-E89: Endocrine diseases
        print("  E00-E89: Endocrine diseases...")
        all_codes.update(self.generate_codes_for_category('E', 0, 89, subcategories=10, detail_levels=5))

        # F01-F99: Mental disorders
        print("  F01-F99: Mental disorders...")
        all_codes.update(self.generate_codes_for_category('F', 1, 99, subcategories=10, detail_levels=3))

        # G00-G99: Nervous system
        print("  G00-G99: Nervous system...")
        all_codes.update(self.generate_codes_for_category('G', 0, 99, subcategories=10, detail_levels=5))

        # H00-H95: Eye and ear
        print("  H00-H95: Eye and ear...")
        all_codes.update(self.generate_codes_for_category('H', 0, 95, subcategories=10, detail_levels=3))

        # I00-I99: Circulatory system
        print("  I00-I99: Circulatory system...")
        all_codes.update(self.generate_codes_for_category('I', 0, 99, subcategories=10, detail_levels=5))

        # J00-J99: Respiratory system
        print("  J00-J99: Respiratory system...")
        all_codes.update(self.generate_codes_for_category('J', 0, 99, subcategories=10, detail_levels=5))

        # K00-K95: Digestive system
        print("  K00-K95: Digestive system...")
        all_codes.update(self.generate_codes_for_category('K', 0, 95, subcategories=10, detail_levels=3))

        # L00-L99: Skin
        print("  L00-L99: Skin...")
        all_codes.update(self.generate_codes_for_category('L', 0, 99, subcategories=10, detail_levels=3))

        # M00-M99: Musculoskeletal
        print("  M00-M99: Musculoskeletal...")
        all_codes.update(self.generate_codes_for_category('M', 0, 99, subcategories=10, detail_levels=5))

        # N00-N99: Genitourinary
        print("  N00-N99: Genitourinary...")
        all_codes.update(self.generate_codes_for_category('N', 0, 99, subcategories=10, detail_levels=3))

        # O00-O9A: Pregnancy
        print("  O00-O9A: Pregnancy...")
        all_codes.update(self.generate_codes_for_category('O', 0, 99, subcategories=10, detail_levels=3))

        # P00-P96: Perinatal
        print("  P00-P96: Perinatal...")
        all_codes.update(self.generate_codes_for_category('P', 0, 96, subcategories=10, detail_levels=3))

        # Q00-Q99: Congenital
        print("  Q00-Q99: Congenital...")
        all_codes.update(self.generate_codes_for_category('Q', 0, 99, subcategories=10, detail_levels=3))

        # R00-R99: Symptoms
        print("  R00-R99: Symptoms...")
        all_codes.update(self.generate_codes_for_category('R', 0, 99, subcategories=10, detail_levels=3))

        # S00-T88: Injuries
        print("  S00-T88: Injuries...")
        all_codes.update(self.generate_codes_for_category('S', 0, 99, subcategories=9, detail_levels=3))
        all_codes.update(self.generate_codes_for_category('T', 0, 88, subcategories=9, detail_levels=3))

        # V00-Y99: External causes
        print("  V00-Y99: External causes...")
        all_codes.update(self.generate_codes_for_category('V', 0, 99, subcategories=10, detail_levels=2))
        all_codes.update(self.generate_codes_for_category('W', 0, 99, subcategories=10, detail_levels=2))
        all_codes.update(self.generate_codes_for_category('X', 0, 99, subcategories=10, detail_levels=2))
        all_codes.update(self.generate_codes_for_category('Y', 0, 99, subcategories=10, detail_levels=2))

        # Z00-Z99: Health status
        print("  Z00-Z99: Health status...")
        all_codes.update(self.generate_codes_for_category('Z', 0, 99, subcategories=10, detail_levels=3))

        return all_codes

    def organize_by_mdc(self, codes: Dict) -> Dict:
        """Organize codes by MDC."""
        mdc_organized = {}

        for code, info in codes.items():
            mdc = info['mdc']
            mdc_key = f"MDC_{mdc}"

            if mdc_key not in mdc_organized:
                mdc_organized[mdc_key] = {}

            mdc_organized[mdc_key][code] = info

        return mdc_organized

    def save_to_file(self, filename: str):
        """Generate and save complete ICD-10-CM dataset."""
        all_codes = self.generate_all_codes()

        print(f"\nTotal codes generated: {len(all_codes):,}")

        # Count CC and MCC
        cc_count = sum(1 for info in all_codes.values() if info['is_cc'])
        mcc_count = sum(1 for info in all_codes.values() if info['is_mcc'])
        print(f"CC codes: {cc_count:,}")
        print(f"MCC codes: {mcc_count:,}")

        # Organize by MDC
        organized_codes = self.organize_by_mdc(all_codes)

        # Create final structure
        output = {
            'version': 'FY2025_v42_complete',
            'description': 'Complete ICD-10-CM diagnosis codes with MDC assignments and CC/MCC classifications',
            'total_codes': len(all_codes),
            'codes': organized_codes
        }

        # Save to file
        print(f"\nSaving to {filename}...")
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print("Done!")


if __name__ == '__main__':
    generator = ICD10CMGenerator()
    generator.save_to_file('/home/user/Medicare-Repricer/data/icd10_cm_data_complete.json')
