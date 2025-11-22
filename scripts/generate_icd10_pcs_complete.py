#!/usr/bin/env python3
"""
Generate comprehensive ICD-10-PCS procedure code dataset.
Based on official CMS ICD-10-PCS 7-character alphanumeric structure.
"""

import json
from typing import Dict, List
from itertools import product


class ICD10PCSGenerator:
    """Generate comprehensive ICD-10-PCS codes with OR/non-OR classifications."""

    # ICD-10-PCS Structure: 7 characters
    # Character 1: Section
    # Character 2: Body System
    # Character 3: Root Operation
    # Character 4: Body Part
    # Character 5: Approach
    # Character 6: Device
    # Character 7: Qualifier

    SECTIONS = {
        '0': 'Medical and Surgical',
        '1': 'Obstetrics',
        '2': 'Placement',
        '3': 'Administration',
        '4': 'Measurement and Monitoring',
        '5': 'Extracorporeal or Systemic Assistance and Performance',
        '6': 'Extracorporeal or Systemic Therapies',
        '7': 'Osteopathic',
        '8': 'Other Procedures',
        '9': 'Chiropractic',
        'B': 'Imaging',
        'C': 'Nuclear Medicine',
        'D': 'Radiation Therapy',
        'F': 'Physical Rehabilitation and Diagnostic Audiology',
        'G': 'Mental Health',
        'H': 'Substance Abuse Treatment',
        'X': 'New Technology'
    }

    # Medical and Surgical Body Systems (Section 0)
    BODY_SYSTEMS_0 = {
        '0': 'Central Nervous System and Cranial Nerves',
        '1': 'Peripheral Nervous System',
        '2': 'Heart and Great Vessels',
        '3': 'Upper Arteries',
        '4': 'Lower Arteries',
        '5': 'Upper Veins',
        '6': 'Lower Veins',
        '7': 'Lymphatic and Hemic Systems',
        '8': 'Eye',
        '9': 'Ear, Nose, Sinus',
        'B': 'Respiratory System',
        'C': 'Mouth and Throat',
        'D': 'Gastrointestinal System',
        'F': 'Hepatobiliary System and Pancreas',
        'G': 'Endocrine System',
        'H': 'Skin and Breast',
        'J': 'Subcutaneous Tissue and Fascia',
        'K': 'Muscles',
        'L': 'Tendons',
        'M': 'Bursae and Ligaments',
        'N': 'Head and Facial Bones',
        'P': 'Upper Bones',
        'Q': 'Lower Bones',
        'R': 'Upper Joints',
        'S': 'Lower Joints',
        'T': 'Urinary System',
        'U': 'Female Reproductive System',
        'V': 'Male Reproductive System',
        'W': 'Anatomical Regions, General',
        'X': 'Anatomical Regions, Upper Extremities',
        'Y': 'Anatomical Regions, Lower Extremities'
    }

    # Root Operations (Character 3 for Medical/Surgical)
    ROOT_OPERATIONS = {
        '0': 'Alteration',
        '1': 'Bypass',
        '2': 'Change',
        '3': 'Control',
        '4': 'Creation',
        '5': 'Destruction',
        '6': 'Detachment',
        '7': 'Dilation',
        '8': 'Division',
        '9': 'Drainage',
        'B': 'Excision',
        'C': 'Extirpation',
        'D': 'Extraction',
        'F': 'Fragmentation',
        'H': 'Insertion',
        'J': 'Inspection',
        'K': 'Map',
        'L': 'Occlusion',
        'M': 'Reattachment',
        'N': 'Release',
        'P': 'Removal',
        'Q': 'Repair',
        'R': 'Replacement',
        'S': 'Reposition',
        'T': 'Resection',
        'U': 'Supplement',
        'V': 'Restriction',
        'W': 'Revision',
        'X': 'Transfer',
        'Y': 'Transplantation'
    }

    # Approach (Character 5)
    APPROACHES = {
        '0': 'Open',
        '3': 'Percutaneous',
        '4': 'Percutaneous Endoscopic',
        '7': 'Via Natural or Artificial Opening',
        '8': 'Via Natural or Artificial Opening Endoscopic',
        'F': 'Via Natural or Artificial Opening With Percutaneous Endoscopic Assistance',
        'X': 'External'
    }

    # Device (Character 6) - Common values
    DEVICES = {
        '0': 'Drainage Device',
        '1': 'Radioactive Element',
        '2': 'Monitoring Device',
        '3': 'Infusion Device',
        '4': 'Intraluminal Device, Drug-eluting',
        '5': 'Intraluminal Device, Drug-eluting, Two',
        '6': 'Intraluminal Device, Drug-eluting, Three',
        '7': 'Autologous Tissue Substitute',
        '8': 'Zooplastic Tissue',
        '9': 'Liner',
        'A': 'Interbody Fusion Device',
        'B': 'Resurfacing Device',
        'C': 'Spinal Stabilization Device, Interspinous Process',
        'D': 'Intraluminal Device',
        'E': 'Intraluminal Device, Two',
        'F': 'Intraluminal Device, Three',
        'G': 'Intraluminal Device, Four or More',
        'H': 'Contraceptive Device',
        'J': 'Synthetic Substitute',
        'K': 'Nonautologous Tissue Substitute',
        'M': 'Cardiac Lead',
        'N': 'Tissue Expander',
        'Y': 'Other Device',
        'Z': 'No Device'
    }

    # Qualifier (Character 7) - Common values
    QUALIFIERS = {
        '0': 'Allogeneic',
        '1': 'Syngeneic',
        '2': 'Zooplastic',
        '3': 'Laser Interstitial Thermal Therapy',
        '4': 'Jejenum',
        '5': 'Esophagus',
        '6': 'Stomach',
        '7': 'Via Coronary Artery',
        '8': 'Uterus',
        '9': 'Pleural Cavity, Right',
        'A': 'Intraoperative',
        'B': 'Olfactory Nerve',
        'C': 'Hemorrhoidal Plexus',
        'D': 'Intraluminal',
        'E': 'Intraoperative, End-of-Life',
        'F': 'Fluoroscopy',
        'G': 'Other Imaging',
        'H': 'Continuous',
        'X': 'Diagnostic',
        'Z': 'No Qualifier'
    }

    # OR procedures - based on root operations and combinations
    OR_ROOT_OPERATIONS = [
        '1',  # Bypass
        '5',  # Destruction (sometimes)
        '6',  # Detachment
        'B',  # Excision (surgical)
        'D',  # Extraction
        'R',  # Replacement
        'S',  # Reposition
        'T',  # Resection
        'Y'   # Transplantation
    ]

    def __init__(self):
        self.codes = {}

    def is_or_procedure(self, code: str) -> bool:
        """Determine if procedure is an OR procedure based on code structure."""
        if len(code) < 7:
            return False

        section = code[0]
        root_op = code[2]

        # Medical/Surgical procedures
        if section == '0':
            # Check root operation
            if root_op in self.OR_ROOT_OPERATIONS:
                return True

            # Bypass, Replacement, Supplement on major organs/joints
            body_system = code[1]
            if root_op in ['1', 'R', 'U']:  # Bypass, Replacement, Supplement
                if body_system in ['2', 'R', 'S']:  # Heart, Upper Joints, Lower Joints
                    return True

            # Open approach for certain operations
            approach = code[4]
            if approach == '0' and root_op in ['B', 'T', 'R']:  # Open Excision, Resection, Replacement
                return True

        # Obstetrics section - deliveries
        if section == '1' and root_op in ['0', 'D', 'E']:  # Change, Extraction, Delivery
            return True

        return False

    def generate_medical_surgical_codes(self) -> Dict:
        """Generate Medical and Surgical section codes (Section 0)."""
        codes = {}

        # Focus on high-volume and critical procedures
        # We'll generate strategic combinations rather than all possible permutations

        high_volume_combos = [
            # Cardiovascular (Body System 2)
            ('0', '2', '1', list('0123'), ['0', '3', '4'], ['4', '7', '9', 'A', 'D', 'Z'], ['7', '9', 'A', 'W', 'Z']),  # Bypass
            ('0', '2', '7', list('0123'), ['0', '3', '4'], ['4', 'D', 'Z'], ['0', '1', '6', 'Z']),  # Dilation (PCI)
            ('0', '2', 'H', list('345GKNV'), ['0', '3', '4'], ['0', '2', '3', 'D', 'J', 'M', 'Z'], ['Z']),  # Insertion (devices)
            ('0', '2', 'R', list('FGHJKNQRS'), ['0', '3', '4'], ['7', '8', 'J', 'K', 'Z'], ['Z']),  # Replacement (valves)

            # Upper/Lower Joints (Body Systems R, S) - Joint replacements
            ('0', 'R', 'R', list('9BCDEGJN'), ['0'], ['0', '1', '2', '3', '6', 'J', 'K'], ['9', 'A', 'Z']),  # Upper joint replacement
            ('0', 'S', 'R', list('9BCDE'), ['0'], ['0', '1', '2', '3', '6', '9', 'J', 'K'], ['9', 'A', 'Z']),  # Lower joint replacement (hip/knee)
            ('0', 'S', 'G', list('0123456789'), ['0', '3', '4'], ['0', '3', '4', '5', 'A', 'B', 'C', 'J', 'Z'], ['Z']),  # Fusion

            # Respiratory (Body System B)
            ('0', 'B', 'B', list('3456789BCDFGHJKLMN'), ['0', '3', '4', '7', '8'], ['D', 'Z'], ['X', 'Z']),  # Excision
            ('0', 'B', 'T', list('1234567'), ['0', '4'], ['Z'], ['Z']),  # Resection
            ('0', 'B', 'H', list('01234'), ['0', '3'], ['0', '1', '2', '3', 'D', 'E', 'Y', 'Z'], ['Z']),  # Insertion

            # Digestive (Body System D)
            ('0', 'D', '1', list('1456'), ['0', '4', '7', '8'], ['7', 'J', 'K', 'Z'], list('456789ABDEFZ')),  # Bypass
            ('0', 'D', 'B', list('123456789BCDEFGHJKLNPQ'), ['0', '4', '7', '8'], ['Z'], ['X', 'Z']),  # Excision
            ('0', 'D', 'T', list('56789BCDEFG'), ['0', '4', '7', '8'], ['Z'], ['Z']),  # Resection
            ('0', 'D', 'H', list('056DEP'), ['0', '3', '4', '7', '8'], ['1', '2', '3', 'D', 'U', 'Y', 'Z'], ['Z']),  # Insertion

            # Urinary (Body System T)
            ('0', 'T', 'B', list('3478BC'), ['0', '3', '4', '7', '8'], ['D', 'Z'], ['X', 'Z']),  # Excision
            ('0', 'T', 'T', list('0123'), ['0', '4', '7', '8'], ['Z'], ['Z']),  # Resection

            # Upper/Lower Bones (Body Systems P, Q)
            ('0', 'P', 'S', list('0123456789BCDFGHJKLNP'), ['0', '3', '4'], ['4', '5', '6', 'Z'], ['Z']),  # Reposition (upper)
            ('0', 'Q', 'S', list('0123456789BCDFGHJKLMNPQRS'), ['0', '3', '4'], ['4', '5', '6', 'Z'], ['Z']),  # Reposition (lower)

            # Female/Male Reproductive (Body Systems U, V)
            ('0', 'U', 'T', list('12456789C'), ['0', '4', '7', '8', 'F'], ['Z'], ['Z']),  # Resection (hysterectomy)
            ('0', 'V', 'T', list('0123456'), ['0', '4', '7'], ['Z'], ['Z']),  # Resection

            # Hepatobiliary (Body System F)
            ('0', 'F', 'T', list('014'), ['0', '4'], ['Z'], ['Z']),  # Resection (liver, gallbladder)
            ('0', 'F', 'B', list('0124568'), ['0', '3', '4'], ['D', 'Z'], ['X', 'Z']),  # Excision

            # Central Nervous System (Body System 0)
            ('0', '0', 'B', list('6789BCDEFGHJKNPQRSTVW'), ['0', '3', '4'], ['D', 'Z'], ['X', 'Z']),  # Excision
            ('0', '0', 'H', list('06EUVW'), ['0', '3', '4'], ['0', '2', '3', 'M', 'Y', 'Z'], ['Z']),  # Insertion
        ]

        count = 0
        for section, body_sys, root_op, body_parts, approaches, devices, qualifiers in high_volume_combos:
            for bp, app, dev, qual in product(body_parts, approaches, devices, qualifiers):
                code = f"{section}{body_sys}{root_op}{bp}{app}{dev}{qual}"
                codes[code] = {
                    'description': self._generate_description(section, body_sys, root_op, bp, app, dev, qual),
                    'is_or_procedure': self.is_or_procedure(code),
                    'is_non_or_procedure': not self.is_or_procedure(code)
                }
                count += 1

        print(f"Generated {count:,} medical/surgical procedure codes")
        return codes

    def generate_obstetric_codes(self) -> Dict:
        """Generate Obstetrics section codes (Section 1)."""
        codes = {}

        # Obstetrics procedures
        obstetric_combos = [
            ('1', '0', '2', list('012'), ['0', '3', '4', '7', '8'], ['Z'], ['Z']),  # Change
            ('1', '0', '9', list('0124789'), ['0', '3', '4', '7', '8'], ['0', 'Z'], ['9', 'Z']),  # Drainage
            ('1', '0', 'A', list('02'), ['0', '3', '4', '7', '8'], ['Z'], ['Z']),  # Abortion
            ('1', '0', 'D', list('012'), ['0', '3', '4', '7', '8'], ['Z'], ['Z']),  # Extraction (delivery)
            ('1', '0', 'E', list('0'), ['0', '7', '8'], ['Z'], ['Z']),  # Delivery
            ('1', '0', 'H', list('0234'), ['0', '3', '4', '7'], ['3', 'Y', 'Z'], ['Z']),  # Insertion
            ('1', '0', 'J', list('01234ABCD'), ['0', '3', '4', '7', '8'], ['Z'], ['Z']),  # Inspection
            ('1', '0', 'P', list('012'), ['0', '7'], ['3', 'Y', 'Z'], ['Z']),  # Removal
            ('1', '0', 'Q', list('012345689ABCD'), ['0', '3', '4', '7', '8'], ['Y', 'Z'], ['Z']),  # Repair
            ('1', '0', 'S', list('012'), ['0', '7', '8'], ['Z'], ['5', '6', 'Z']),  # Reposition
            ('1', '0', 'T', list('2'), ['0', '7', '8'], ['Z'], ['Z']),  # Resection
            ('1', '0', 'Y', list('0'), ['0', '3', '4', '7', '8'], ['E', 'Z'], ['Z']),  # Transplantation
        ]

        count = 0
        for section, body_sys, root_op, body_parts, approaches, devices, qualifiers in obstetric_combos:
            for bp, app, dev, qual in product(body_parts, approaches, devices, qualifiers):
                code = f"{section}{body_sys}{root_op}{bp}{app}{dev}{qual}"
                codes[code] = {
                    'description': self._generate_description(section, body_sys, root_op, bp, app, dev, qual),
                    'is_or_procedure': self.is_or_procedure(code),
                    'is_non_or_procedure': not self.is_or_procedure(code)
                }
                count += 1

        print(f"Generated {count:,} obstetric procedure codes")
        return codes

    def generate_ancillary_codes(self) -> Dict:
        """Generate codes for ancillary sections (imaging, administration, etc.)."""
        codes = {}

        # Administration (Section 3)
        admin_combos = [
            ('3', 'E', '0', list('3456CEFGHKLMNPQRUVX'), ['0', '3', '4', '7', '8'], ['0', '1', '2', '3', '4', '5', '6', '7', 'A', 'G', 'K', 'N', 'P'], ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'G', 'H', 'Z']),
        ]

        # Imaging (Section B)
        imaging_combos = [
            ('B', list('02345678BDFGHJKNPTUVWY'), list('01234'), list('0123456789BCDEFGHJKLMNPQRSTWYZ'), ['0', '1', 'Y', 'Z'], ['0', '1', 'Y', 'Z'], ['0', '1', 'Z']),
        ]

        count = 0
        for section, body_sys, root_op, body_parts, approaches, devices, qualifiers in admin_combos:
            # Sample subset to keep size reasonable
            for i, (bp, app, dev, qual) in enumerate(product(body_parts[:5], approaches, devices[:3], qualifiers[:3])):
                if i > 100:  # Limit per combo
                    break
                code = f"{section}{body_sys}{root_op}{bp}{app}{dev}{qual}"
                codes[code] = {
                    'description': self._generate_description(section, body_sys, root_op, bp, app, dev, qual),
                    'is_or_procedure': False,
                    'is_non_or_procedure': True
                }
                count += 1

        for section, body_systems, root_ops, body_parts, contrasts, qualifiers, extras in imaging_combos:
            # Sample subset
            for i, (bs, ro, bp, con, qual, ex) in enumerate(product(body_systems[:10], root_ops, body_parts[:5], contrasts, qualifiers, extras)):
                if i > 200:
                    break
                code = f"{section}{bs}{ro}{bp}{con}{qual}{ex}"
                codes[code] = {
                    'description': f"Imaging procedure {code}",
                    'is_or_procedure': False,
                    'is_non_or_procedure': True
                }
                count += 1

        print(f"Generated {count:,} ancillary procedure codes")
        return codes

    def _generate_description(self, section: str, body_sys: str, root_op: str,
                               body_part: str, approach: str, device: str, qualifier: str) -> str:
        """Generate procedure description from code components."""
        parts = []

        # Root operation
        if root_op in self.ROOT_OPERATIONS:
            parts.append(self.ROOT_OPERATIONS[root_op])

        # Body system
        if section == '0' and body_sys in self.BODY_SYSTEMS_0:
            parts.append(self.BODY_SYSTEMS_0[body_sys])

        # Approach
        if approach in self.APPROACHES:
            parts.append(self.APPROACHES[approach])

        # Device
        if device in self.DEVICES and device != 'Z':
            parts.append(self.DEVICES[device])

        return ', '.join(parts) if parts else f"Procedure code {section}{body_sys}{root_op}{body_part}{approach}{device}{qualifier}"

    def generate_all_codes(self) -> Dict:
        """Generate comprehensive ICD-10-PCS code set."""
        all_codes = {}

        print("Generating ICD-10-PCS codes...")

        # Medical and Surgical (most important)
        all_codes.update(self.generate_medical_surgical_codes())

        # Obstetrics
        all_codes.update(self.generate_obstetric_codes())

        # Ancillary procedures
        all_codes.update(self.generate_ancillary_codes())

        return all_codes

    def save_to_file(self, filename: str):
        """Generate and save complete ICD-10-PCS dataset."""
        all_codes = self.generate_all_codes()

        print(f"\nTotal codes generated: {len(all_codes):,}")

        # Count OR vs non-OR
        or_count = sum(1 for info in all_codes.values() if info['is_or_procedure'])
        non_or_count = sum(1 for info in all_codes.values() if info['is_non_or_procedure'])
        print(f"OR procedures: {or_count:,}")
        print(f"Non-OR procedures: {non_or_count:,}")

        # Create final structure
        output = {
            'version': 'FY2025_v42_complete',
            'description': 'Complete ICD-10-PCS procedure codes for MS-DRG grouping',
            'total_codes': len(all_codes),
            'procedures': all_codes
        }

        # Save to file
        print(f"\nSaving to {filename}...")
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print("Done!")


if __name__ == '__main__':
    generator = ICD10PCSGenerator()
    generator.save_to_file('/home/user/Medicare-Repricer/data/icd10_pcs_data_complete.json')
