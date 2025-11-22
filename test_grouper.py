"""
Test MS-DRG Grouper

This test suite validates the MS-DRG grouping functionality.
"""

import pytest
from pathlib import Path
from medicare_repricing import MSDRGGrouper, GrouperInput


def test_grouper_initialization():
    """Test that the grouper initializes correctly with data files."""
    grouper = MSDRGGrouper(data_directory=Path("data"))
    assert grouper is not None
    assert len(grouper.diagnosis_lookup) > 0
    assert len(grouper.procedure_lookup) > 0
    assert len(grouper.drg_lookup) > 0


def test_hip_replacement_without_mcc():
    """Test MS-DRG 470: Major joint replacement without MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="M16.11",  # Primary osteoarthritis, right hip
        secondary_diagnoses=["I10"],  # Hypertension (not a CC/MCC)
        procedures=["0SR9019"],  # Hip replacement
        age=72,
        sex="F"
    ))

    assert result.ms_drg == "470"
    assert result.mdc == "08"
    assert result.drg_type == "SURGICAL"
    assert result.has_mcc is False
    assert "musculoskeletal" in result.mdc_description.lower()
    assert result.relative_weight is not None


def test_hip_replacement_with_mcc():
    """Test MS-DRG 469: Major joint replacement with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="M16.11",  # Primary osteoarthritis, right hip
        secondary_diagnoses=["N17.9", "I10"],  # Acute kidney failure (MCC) + HTN
        procedures=["0SR9019"],  # Hip replacement
        age=72,
        sex="F"
    ))

    assert result.ms_drg == "469"
    assert result.mdc == "08"
    assert result.drg_type == "SURGICAL"
    assert result.has_mcc is True
    assert result.mcc_list is not None
    assert len(result.mcc_list) == 1


def test_ami_with_mcc():
    """Test MS-DRG 280: Acute Myocardial Infarction with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.09",  # STEMI
        secondary_diagnoses=["J96.00", "I50.9"],  # Acute respiratory failure (MCC) + heart failure (CC)
        age=68,
        sex="M"
    ))

    assert result.ms_drg == "280"
    assert result.mdc == "05"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is True
    assert result.has_cc is True  # Also has a CC in addition to MCC


def test_ami_without_mcc():
    """Test MS-DRG 282: Acute Myocardial Infarction without CC/MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.09",  # STEMI
        secondary_diagnoses=[],  # No complications
        age=55,
        sex="M"
    ))

    assert result.ms_drg == "282"
    assert result.mdc == "05"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is False
    assert result.has_cc is False


def test_heart_failure_with_cc():
    """Test MS-DRG 292: Heart failure with CC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I50.23",  # Acute on chronic systolic CHF
        secondary_diagnoses=["E87.5", "I10"],  # Hyperkalemia (CC) + HTN
        age=75,
        sex="F"
    ))

    assert result.ms_drg == "292"
    assert result.mdc == "05"
    assert result.drg_type == "MEDICAL"
    assert result.has_cc is True
    assert result.has_mcc is False


def test_septicemia_with_mcc():
    """Test MS-DRG 871: Septicemia with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="A41.9",  # Sepsis, unspecified
        secondary_diagnoses=["R65.20", "N17.9"],  # Severe sepsis (MCC) + AKI (MCC)
        age=82,
        sex="M"
    ))

    assert result.ms_drg == "871"
    assert result.mdc == "18"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is True
    assert len(result.mcc_list) >= 1


def test_pneumonia_with_mcc():
    """Test MS-DRG 193: Pneumonia with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="J18.9",  # Pneumonia, unspecified
        secondary_diagnoses=["J96.01", "D62"],  # Acute respiratory failure (MCC) + anemia (CC)
        age=78,
        sex="F"
    ))

    assert result.ms_drg == "193"
    assert result.mdc == "04"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is True


def test_copd_without_cc_mcc():
    """Test MS-DRG 192: COPD without CC/MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="J44.1",  # COPD with exacerbation
        secondary_diagnoses=[],  # No complications
        age=65,
        sex="M"
    ))

    assert result.ms_drg == "192"
    assert result.mdc == "04"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is False
    assert result.has_cc is False


def test_knee_replacement():
    """Test knee replacement procedure grouping."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="M17.11",  # Primary osteoarthritis, right knee
        secondary_diagnoses=["I10", "E11.9"],  # HTN + diabetes (non-CC)
        procedures=["0SRC0J9"],  # Knee replacement
        age=68,
        sex="F"
    ))

    assert result.ms_drg == "470"  # Same family as hip replacement
    assert result.mdc == "08"
    assert result.drg_type == "SURGICAL"


def test_cabg_with_mcc():
    """Test MS-DRG 231: Coronary bypass with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.01",  # STEMI involving left main
        secondary_diagnoses=["J96.00", "N17.9"],  # Respiratory failure + AKI (both MCC)
        procedures=["02100Z9"],  # CABG from left internal mammary
        age=70,
        sex="M"
    ))

    assert result.ms_drg == "231"
    assert result.mdc == "05"
    assert result.drg_type == "SURGICAL"
    assert result.has_mcc is True


def test_pci_percutaneous_coronary_intervention():
    """Test MS-DRG 246-248: PCI (Percutaneous Coronary Intervention)."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I21.02",  # STEMI involving LAD
        secondary_diagnoses=["I50.21", "E87.1"],  # Acute systolic CHF (CC) + hyponatremia (CC)
        procedures=["027034Z"],  # PCI with drug-eluting stent
        age=65,
        sex="M"
    ))

    # Should group to PCI with CC
    assert result.ms_drg == "247"
    assert result.mdc == "05"
    assert result.drg_type == "SURGICAL"
    assert result.has_cc is True


def test_spinal_fusion():
    """Test spinal fusion procedures."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="M48.061",  # Spinal stenosis, lumbar region
        secondary_diagnoses=["I10"],  # Hypertension (not CC)
        procedures=["0SG70J0"],  # Spinal fusion
        age=62,
        sex="F"
    ))

    assert result.ms_drg == "455"  # Spinal fusion without CC/MCC
    assert result.mdc == "08"
    assert result.drg_type == "SURGICAL"


def test_acute_renal_failure():
    """Test acute kidney failure medical DRG."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="N17.9",  # Acute kidney failure
        secondary_diagnoses=["E87.5", "D64.9"],  # Hyperkalemia (CC) + anemia
        age=70,
        sex="M"
    ))

    assert result.ms_drg == "683"  # AKI with CC
    assert result.mdc == "11"
    assert result.drg_type == "MEDICAL"
    assert result.has_cc is True


def test_diabetes_with_mcc():
    """Test diabetes with MCC."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="E11.01",  # Type 2 diabetes with hyperosmolarity with coma
        secondary_diagnoses=["N17.9"],  # Acute kidney failure (MCC)
        age=68,
        sex="F"
    ))

    assert result.ms_drg == "637"  # Diabetes with MCC
    assert result.mdc == "10"
    assert result.drg_type == "MEDICAL"
    assert result.has_mcc is True


def test_stroke_cerebral_infarction():
    """Test stroke/cerebral infarction."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="I63.00",  # Cerebral infarction
        secondary_diagnoses=["I10", "E11.9"],  # HTN + diabetes (non-CC for this PDX)
        age=74,
        sex="M"
    ))

    assert result.ms_drg == "066"  # Stroke without CC/MCC
    assert result.mdc == "01"
    assert result.drg_type == "MEDICAL"


def test_invalid_diagnosis():
    """Test handling of invalid diagnosis codes."""
    grouper = MSDRGGrouper(data_directory=Path("data"))

    result = grouper.assign_drg(GrouperInput(
        principal_diagnosis="INVALID123",  # Invalid code
        age=50,
        sex="M"
    ))

    assert result.error_messages is not None
    assert len(result.error_messages) > 0
    assert "not found" in result.error_messages[0].lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
