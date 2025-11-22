"""
MS-DRG Grouper Data Models

This module defines data structures for the MS-DRG grouper,
which assigns Medicare Severity Diagnosis Related Groups based on
ICD-10 diagnosis and procedure codes.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GrouperInput(BaseModel):
    """
    Input data for MS-DRG grouping.

    This represents all the clinical and demographic information
    needed to assign an MS-DRG to an inpatient hospital stay.
    """
    # Diagnosis codes (ICD-10-CM)
    principal_diagnosis: str = Field(
        ...,
        description="Principal diagnosis code (ICD-10-CM), e.g., 'I21.09'"
    )
    secondary_diagnoses: Optional[List[str]] = Field(
        default=None,
        description="Secondary diagnosis codes (ICD-10-CM), e.g., ['I10', 'E11.9']"
    )

    # Procedure codes (ICD-10-PCS)
    procedures: Optional[List[str]] = Field(
        default=None,
        description="ICD-10-PCS procedure codes, e.g., ['02100Z9', '02110A4']"
    )

    # Patient demographics
    age: int = Field(
        ...,
        ge=0,
        le=120,
        description="Patient age in years at admission"
    )
    sex: str = Field(
        ...,
        description="Patient sex: 'M' for male, 'F' for female, 'U' for unknown"
    )

    # Discharge information
    discharge_status: Optional[str] = Field(
        default="01",
        description="Patient discharge status code (e.g., '01' = home, '20' = expired)"
    )

    # Additional clinical information
    length_of_stay: Optional[int] = Field(
        default=None,
        ge=0,
        description="Length of stay in days"
    )
    admit_diagnosis: Optional[str] = Field(
        default=None,
        description="Admit diagnosis code (ICD-10-CM)"
    )


class GrouperOutput(BaseModel):
    """
    Output from MS-DRG grouping process.

    This contains the assigned MS-DRG and detailed information
    about how the grouping decision was made.
    """
    # MS-DRG assignment
    ms_drg: str = Field(
        ...,
        description="Assigned MS-DRG code, e.g., '470'"
    )
    drg_description: str = Field(
        ...,
        description="MS-DRG description, e.g., 'Major joint replacement or reattachment of lower extremity w/o MCC'"
    )

    # Grouping details
    mdc: str = Field(
        ...,
        description="Major Diagnostic Category (00-25)"
    )
    mdc_description: str = Field(
        ...,
        description="MDC description, e.g., 'Diseases and Disorders of the Musculoskeletal System'"
    )

    # Classification
    drg_type: str = Field(
        ...,
        description="DRG type: 'SURGICAL', 'MEDICAL', or 'PRE-MDC'"
    )

    # Severity indicators
    has_mcc: bool = Field(
        default=False,
        description="Whether any Major Complication/Comorbidity (MCC) was present"
    )
    has_cc: bool = Field(
        default=False,
        description="Whether any Complication/Comorbidity (CC) was present (excluding MCCs)"
    )
    mcc_list: Optional[List[str]] = Field(
        default=None,
        description="List of ICD-10 codes that qualified as MCCs"
    )
    cc_list: Optional[List[str]] = Field(
        default=None,
        description="List of ICD-10 codes that qualified as CCs"
    )

    # Related payment information (from MS-DRG data)
    relative_weight: Optional[float] = Field(
        default=None,
        description="DRG relative weight for payment calculation"
    )
    geometric_mean_los: Optional[float] = Field(
        default=None,
        description="Geometric mean length of stay for this DRG"
    )
    arithmetic_mean_los: Optional[float] = Field(
        default=None,
        description="Arithmetic mean length of stay for this DRG"
    )

    # Grouping process details
    grouping_version: str = Field(
        default="43.0",
        description="MS-DRG grouper version (e.g., '43.0' for FY 2026)"
    )
    warning_messages: Optional[List[str]] = Field(
        default=None,
        description="Warning messages from grouping process"
    )
    error_messages: Optional[List[str]] = Field(
        default=None,
        description="Error messages from grouping process"
    )


class ICD10Diagnosis(BaseModel):
    """
    ICD-10-CM diagnosis code with metadata for grouping.
    """
    code: str = Field(..., description="ICD-10-CM code")
    description: str = Field(..., description="Code description")
    mdc: str = Field(..., description="Major Diagnostic Category (00-25)")
    is_cc: bool = Field(default=False, description="Is a Complication/Comorbidity")
    is_mcc: bool = Field(default=False, description="Is a Major Complication/Comorbidity")
    cc_exclusions: Optional[List[str]] = Field(
        default=None,
        description="Principal diagnoses for which this code is excluded as CC/MCC"
    )


class ICD10Procedure(BaseModel):
    """
    ICD-10-PCS procedure code with metadata for grouping.
    """
    code: str = Field(..., description="ICD-10-PCS code")
    description: str = Field(..., description="Procedure description")
    is_or_procedure: bool = Field(
        default=False,
        description="Whether this is an Operating Room (OR) procedure"
    )
    is_non_or_procedure: bool = Field(
        default=False,
        description="Whether this is a significant non-OR procedure"
    )
    affects_drg: bool = Field(
        default=True,
        description="Whether this procedure affects DRG assignment"
    )


class MDCDefinition(BaseModel):
    """
    Definition of a Major Diagnostic Category.
    """
    code: str = Field(..., description="MDC code (00-25)")
    name: str = Field(..., description="MDC name")
    description: str = Field(..., description="Detailed description")
    body_system: Optional[str] = Field(
        default=None,
        description="Primary body system or specialty"
    )
    special_logic: Optional[str] = Field(
        default=None,
        description="Special grouping logic (e.g., for MDC 24, 25)"
    )


class DRGDefinition(BaseModel):
    """
    Definition of an MS-DRG with grouping criteria.
    """
    ms_drg: str = Field(..., description="MS-DRG code")
    description: str = Field(..., description="DRG description")
    mdc: str = Field(..., description="Major Diagnostic Category")
    drg_type: str = Field(..., description="SURGICAL, MEDICAL, or PRE-MDC")
    relative_weight: float = Field(..., description="DRG relative weight")
    geometric_mean_los: Optional[float] = Field(default=None, description="GMLOS")
    arithmetic_mean_los: Optional[float] = Field(default=None, description="ALOS")

    # Grouping criteria
    requires_or_procedure: bool = Field(
        default=False,
        description="Requires an OR procedure"
    )
    specific_procedures: Optional[List[str]] = Field(
        default=None,
        description="Specific procedure codes that group to this DRG"
    )
    specific_diagnoses: Optional[List[str]] = Field(
        default=None,
        description="Specific diagnosis codes that group to this DRG"
    )
    severity_level: Optional[str] = Field(
        default=None,
        description="Severity: 'WITH_MCC', 'WITH_CC', 'WITHOUT_CC_MCC'"
    )
