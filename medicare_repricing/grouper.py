"""
MS-DRG Grouper

This module implements the CMS Medicare Severity Diagnosis Related Groups (MS-DRG)
grouper algorithm. It assigns MS-DRG codes to inpatient hospital stays based on
ICD-10 diagnosis codes, ICD-10-PCS procedure codes, and patient demographics.

Usage:
    from medicare_repricing.grouper import MSDRGGrouper
    from medicare_repricing.grouper_models import GrouperInput

    grouper = MSDRGGrouper(data_directory="data")

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.09",
        secondary_diagnoses=["I10", "E11.9"],
        procedures=["027034Z"],
        age=65,
        sex="M"
    ))

    print(f"MS-DRG: {result.ms_drg} - {result.drg_description}")
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .grouper_models import GrouperInput, GrouperOutput
from .models import RepricedClaimLine


class MSDRGGrouper:
    """
    MS-DRG Grouper for assigning Medicare Severity Diagnosis Related Groups.

    This implements the CMS MS-DRG grouping algorithm which determines
    the appropriate DRG based on clinical and demographic information.
    """

    def __init__(self, data_directory: Path):
        """
        Initialize the MS-DRG Grouper with data files.

        Args:
            data_directory: Path to directory containing grouper data files
        """
        self.data_dir = Path(data_directory)

        # Load all data files
        self.icd10_cm_data = self._load_json("icd10_cm_data.json")
        self.icd10_pcs_data = self._load_json("icd10_pcs_data.json")
        self.mdc_definitions = self._load_json("mdc_definitions.json")
        self.grouping_rules = self._load_json("drg_grouping_rules.json")
        self.ms_drg_data = self._load_json("ms_drg_data.json")

        # Build lookup indexes for performance
        self._build_indexes()

    def _load_json(self, filename: str) -> Dict:
        """Load a JSON data file."""
        file_path = self.data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Required data file not found: {file_path}")

        with open(file_path, 'r') as f:
            return json.load(f)

    def _build_indexes(self):
        """
        Build lookup indexes for fast data access.

        This creates flattened indexes of all ICD-10 codes for quick lookups.
        """
        # Flatten ICD-10-CM codes into a single lookup dictionary
        self.diagnosis_lookup = {}
        for category, codes in self.icd10_cm_data.get("codes", {}).items():
            # Skip metadata fields like _comment
            if category.startswith("_"):
                continue
            # Ensure codes is a dictionary
            if isinstance(codes, dict):
                for code, data in codes.items():
                    self.diagnosis_lookup[code] = data

        # Flatten ICD-10-PCS codes
        self.procedure_lookup = {}
        for category, procedures in self.icd10_pcs_data.get("procedures", {}).items():
            # Skip metadata fields like _comment
            if category.startswith("_"):
                continue
            # Ensure procedures is a dictionary
            if isinstance(procedures, dict):
                for code, data in procedures.items():
                    self.procedure_lookup[code] = data

        # Index MS-DRG data by DRG code
        self.drg_lookup = {}
        # ms_drg_data is a list, not a dict
        drg_list = self.ms_drg_data if isinstance(self.ms_drg_data, list) else self.ms_drg_data.get("drgs", [])
        for drg in drg_list:
            self.drg_lookup[drg["ms_drg"]] = drg

    def assign_drg(self, input_data: GrouperInput) -> GrouperOutput:
        """
        Assign an MS-DRG based on clinical and demographic information.

        This is the main entry point for MS-DRG grouping.

        Args:
            input_data: GrouperInput with diagnosis codes, procedures, demographics

        Returns:
            GrouperOutput with assigned MS-DRG and grouping details
        """
        warnings = []
        errors = []

        # Step 1: Validate principal diagnosis
        pdx = input_data.principal_diagnosis.upper().replace(".", "")
        pdx_data = self._lookup_diagnosis(pdx)

        if not pdx_data:
            errors.append(f"Principal diagnosis '{input_data.principal_diagnosis}' not found in grouper database")
            # Return a default/error DRG
            return self._create_error_output(input_data, errors)

        # Step 2: Determine MDC from principal diagnosis
        mdc = pdx_data.get("mdc")
        mdc_info = self.mdc_definitions["mdcs"].get(mdc, {})

        # Step 3: Check for Pre-MDC assignments (highest priority)
        if mdc == "00":
            # Pre-MDC cases (transplants, tracheostomy, ECMO, etc.)
            pre_mdc_result = self._assign_pre_mdc(input_data, pdx_data)
            if pre_mdc_result:
                return pre_mdc_result

        # Step 4: Check for procedures (surgical vs. medical DRG)
        has_or_procedure, or_procedures = self._check_or_procedures(input_data.procedures)

        # Step 5: Determine CC/MCC presence
        has_mcc, has_cc, mcc_list, cc_list = self._determine_cc_mcc(
            pdx,
            input_data.secondary_diagnoses or []
        )

        # Step 6: Apply grouping logic based on MDC
        assigned_drg = None
        drg_type = "MEDICAL"

        if has_or_procedure:
            # Surgical DRG path
            drg_type = "SURGICAL"
            assigned_drg = self._assign_surgical_drg(
                mdc, or_procedures, has_mcc, has_cc, pdx, input_data
            )

        if not assigned_drg:
            # Medical DRG path
            drg_type = "MEDICAL"
            assigned_drg = self._assign_medical_drg(
                mdc, pdx, has_mcc, has_cc, input_data
            )

        # Step 7: If no DRG assigned, use default for MDC
        if not assigned_drg:
            warnings.append(f"No specific DRG rule matched; using default for MDC {mdc}")
            assigned_drg = self._get_default_drg_for_mdc(mdc, has_mcc, has_cc)

        # Step 8: Get DRG details
        drg_details = self.drg_lookup.get(assigned_drg, {})

        # Step 9: Build output
        return GrouperOutput(
            ms_drg=assigned_drg,
            drg_description=drg_details.get("description", f"MS-DRG {assigned_drg}"),
            mdc=mdc,
            mdc_description=mdc_info.get("description", f"MDC {mdc}"),
            drg_type=drg_type,
            has_mcc=has_mcc,
            has_cc=has_cc,
            mcc_list=mcc_list if mcc_list else None,
            cc_list=cc_list if cc_list else None,
            relative_weight=drg_details.get("relative_weight"),
            geometric_mean_los=drg_details.get("geometric_mean_los"),
            arithmetic_mean_los=drg_details.get("arithmetic_mean_los"),
            grouping_version="43.0",
            warning_messages=warnings if warnings else None,
            error_messages=errors if errors else None
        )

    def _lookup_diagnosis(self, code: str) -> Optional[Dict]:
        """
        Look up an ICD-10-CM diagnosis code.

        Handles codes with or without decimal points.
        """
        # Try exact match first
        code_clean = code.upper().replace(".", "")
        if code_clean in self.diagnosis_lookup:
            return self.diagnosis_lookup[code_clean]

        # Try with decimal point in standard position (after 3rd character)
        if len(code_clean) > 3:
            code_with_decimal = code_clean[:3] + "." + code_clean[3:]
            if code_with_decimal in self.diagnosis_lookup:
                return self.diagnosis_lookup[code_with_decimal]

        return None

    def _check_or_procedures(self, procedures: Optional[List[str]]) -> Tuple[bool, List[str]]:
        """
        Check if any procedures are OR (Operating Room) procedures.

        Returns:
            Tuple of (has_or_procedure, list_of_or_procedure_codes)
        """
        if not procedures:
            return False, []

        or_procedures = []
        for proc in procedures:
            proc_clean = proc.upper().replace(".", "")
            proc_data = self.procedure_lookup.get(proc_clean)

            if proc_data and proc_data.get("is_or_procedure", False):
                or_procedures.append(proc_clean)

        return len(or_procedures) > 0, or_procedures

    def _determine_cc_mcc(
        self,
        principal_dx: str,
        secondary_diagnoses: List[str]
    ) -> Tuple[bool, bool, List[str], List[str]]:
        """
        Determine presence of Complications/Comorbidities (CC) and Major CC (MCC).

        Args:
            principal_dx: Principal diagnosis code
            secondary_diagnoses: List of secondary diagnosis codes

        Returns:
            Tuple of (has_mcc, has_cc, mcc_list, cc_list)
        """
        has_mcc = False
        has_cc = False
        mcc_list = []
        cc_list = []

        for sdx in secondary_diagnoses:
            sdx_clean = sdx.upper().replace(".", "")
            sdx_data = self._lookup_diagnosis(sdx_clean)

            if not sdx_data:
                continue

            # Check if this diagnosis is excluded as a CC/MCC for this principal diagnosis
            # (In a full implementation, we'd check CC exclusion lists here)

            if sdx_data.get("is_mcc", False):
                has_mcc = True
                mcc_list.append(sdx_clean)
            elif sdx_data.get("is_cc", False):
                has_cc = True
                cc_list.append(sdx_clean)

        return has_mcc, has_cc, mcc_list, cc_list

    def _assign_pre_mdc(
        self,
        input_data: GrouperInput,
        pdx_data: Dict
    ) -> Optional[GrouperOutput]:
        """
        Assign Pre-MDC DRGs for special cases like transplants.

        These have the highest priority in grouping logic.
        """
        # Pre-MDC logic for transplants and other special procedures
        # (Would be fully implemented with actual Pre-MDC rules)
        return None

    def _assign_surgical_drg(
        self,
        mdc: str,
        or_procedures: List[str],
        has_mcc: bool,
        has_cc: bool,
        pdx: str,
        input_data: GrouperInput
    ) -> Optional[str]:
        """
        Assign a surgical MS-DRG based on procedures performed.

        This applies MDC-specific surgical grouping rules.
        """
        # Get surgical rules for this MDC
        mdc_key = self._get_mdc_key(mdc)
        rules = self.grouping_rules.get("grouping_rules", {}).get(mdc_key, {})
        surgical_rules = rules.get("surgical_drgs", {})

        # Try to match procedures to specific surgical DRG families
        for rule_name, rule_data in surgical_rules.items():
            if self._procedure_matches_rule(or_procedures, rule_data):
                # Found a matching rule, now select DRG based on severity
                drgs = rule_data.get("drgs", {})
                return self._select_drg_by_severity(drgs, has_mcc, has_cc)

        return None

    def _assign_medical_drg(
        self,
        mdc: str,
        pdx: str,
        has_mcc: bool,
        has_cc: bool,
        input_data: GrouperInput
    ) -> Optional[str]:
        """
        Assign a medical MS-DRG based on principal diagnosis.

        This applies MDC-specific medical grouping rules.
        """
        # Get medical rules for this MDC
        mdc_key = self._get_mdc_key(mdc)
        rules = self.grouping_rules.get("grouping_rules", {}).get(mdc_key, {})
        medical_rules = rules.get("medical_drgs", {})

        # Try to match principal diagnosis to specific medical DRG families
        for rule_name, rule_data in medical_rules.items():
            if self._diagnosis_matches_rule(pdx, rule_data):
                # Found a matching rule, now select DRG based on severity
                drgs = rule_data.get("drgs", {})
                return self._select_drg_by_severity(drgs, has_mcc, has_cc)

        return None

    def _procedure_matches_rule(self, procedures: List[str], rule: Dict) -> bool:
        """Check if any procedure matches the rule criteria."""
        # Check for specific procedure codes
        if "procedure_codes" in rule:
            for proc_pattern in rule["procedure_codes"]:
                pattern = proc_pattern.replace("*", ".*").replace(".", "\\.")
                for proc in procedures:
                    if re.match(pattern, proc):
                        return True

        # Check for procedure pattern
        if "procedure_pattern" in rule:
            pattern = rule["procedure_pattern"].replace("*", ".*").replace(".", "\\.")
            for proc in procedures:
                if re.match(pattern, proc):
                    return True

        return False

    def _diagnosis_matches_rule(self, diagnosis: str, rule: Dict) -> bool:
        """Check if diagnosis matches the rule criteria."""
        if "principal_diagnosis_pattern" in rule:
            pattern = rule["principal_diagnosis_pattern"]
            if re.match(pattern, diagnosis):
                return True

        if "specific_diagnoses" in rule:
            if diagnosis in rule["specific_diagnoses"]:
                return True

        return False

    def _select_drg_by_severity(self, drgs: Dict, has_mcc: bool, has_cc: bool) -> str:
        """
        Select the appropriate DRG from a family based on CC/MCC presence.

        Args:
            drgs: Dictionary with keys like 'with_mcc', 'with_cc', 'without_cc_mcc'
            has_mcc: Whether patient has an MCC
            has_cc: Whether patient has a CC

        Returns:
            MS-DRG code as a string
        """
        if has_mcc and "with_mcc" in drgs:
            return drgs["with_mcc"]
        elif (has_cc or has_mcc) and "with_cc" in drgs:
            return drgs["with_cc"]
        elif "without_cc_mcc" in drgs:
            return drgs["without_cc_mcc"]
        elif "without_mcc" in drgs:
            return drgs["without_mcc"]
        else:
            # Return first available DRG
            return list(drgs.values())[0]

    def _get_mdc_key(self, mdc: str) -> str:
        """Convert MDC code to lookup key format."""
        mdc_names = {
            "00": "MDC_00_PRE_MDC",
            "01": "MDC_01_NERVOUS",
            "04": "MDC_04_RESPIRATORY",
            "05": "MDC_05_CIRCULATORY",
            "06": "MDC_06_DIGESTIVE",
            "08": "MDC_08_MUSCULOSKELETAL",
            "10": "MDC_10_ENDOCRINE",
            "11": "MDC_11_KIDNEY_URINARY",
            "18": "MDC_18_INFECTIOUS_DISEASE"
        }
        return mdc_names.get(mdc, f"MDC_{mdc}")

    def _get_default_drg_for_mdc(self, mdc: str, has_mcc: bool, has_cc: bool) -> str:
        """
        Get a default DRG for an MDC when no specific rule matches.

        This is a fallback to ensure a DRG is always assigned.
        """
        # Default DRGs by MDC (these are approximate fallbacks)
        defaults = {
            "01": {"with_mcc": "100", "with_cc": "101", "without_cc_mcc": "102"},
            "04": {"with_mcc": "189", "with_cc": "190", "without_cc_mcc": "191"},
            "05": {"with_mcc": "291", "with_cc": "292", "without_cc_mcc": "293"},
            "06": {"with_mcc": "389", "with_cc": "390", "without_cc_mcc": "391"},
            "08": {"with_mcc": "548", "with_cc": "549", "without_cc_mcc": "550"},
            "10": {"with_mcc": "640", "with_cc": "641", "without_cc_mcc": "642"},
            "11": {"with_mcc": "689", "with_cc": "690", "without_cc_mcc": "691"},
            "18": {"with_mcc": "871", "without_mcc": "872"}
        }

        mdc_defaults = defaults.get(mdc, {"without_cc_mcc": "999"})
        return self._select_drg_by_severity(mdc_defaults, has_mcc, has_cc)

    def _create_error_output(self, input_data: GrouperInput, errors: List[str]) -> GrouperOutput:
        """Create an error output when grouping fails."""
        return GrouperOutput(
            ms_drg="999",
            drg_description="Ungroupable - Invalid Data",
            mdc="00",
            mdc_description="Ungroupable",
            drg_type="ERROR",
            has_mcc=False,
            has_cc=False,
            grouping_version="43.0",
            error_messages=errors
        )
