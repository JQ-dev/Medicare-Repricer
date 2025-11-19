"""
Data models for Medicare claims and repricing.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ClaimLine(BaseModel):
    """Represents a single line item on a medical claim."""

    line_number: int = Field(..., description="Sequential line number", ge=1)
    procedure_code: str = Field(..., description="CPT or HCPCS procedure code")
    modifier: Optional[str] = Field(None, description="Procedure modifier (e.g., 26, TC, 50)")
    place_of_service: str = Field(..., description="Two-digit place of service code")
    locality: str = Field(..., description="Medicare locality code for GPCI")
    units: int = Field(1, description="Number of units", ge=1)
    diagnosis_pointers: Optional[List[int]] = Field(
        None,
        description="Pointers to diagnosis codes (1-based index)"
    )

    @field_validator('procedure_code')
    @classmethod
    def validate_procedure_code(cls, v: str) -> str:
        """Validate and normalize procedure code."""
        if not v or not v.strip():
            raise ValueError("Procedure code cannot be empty")
        return v.strip().upper()

    @field_validator('place_of_service')
    @classmethod
    def validate_place_of_service(cls, v: str) -> str:
        """Validate place of service code."""
        v = v.strip()
        if not v.isdigit() or len(v) != 2:
            raise ValueError("Place of service must be a 2-digit code")
        return v


class Claim(BaseModel):
    """Represents a complete medical claim."""

    claim_id: str = Field(..., description="Unique claim identifier")
    patient_id: str = Field(..., description="Patient identifier")
    diagnosis_codes: List[str] = Field(
        ...,
        description="List of ICD-10 diagnosis codes",
        min_length=1
    )
    lines: List[ClaimLine] = Field(
        ...,
        description="List of claim line items",
        min_length=1
    )

    @field_validator('diagnosis_codes')
    @classmethod
    def validate_diagnosis_codes(cls, v: List[str]) -> List[str]:
        """Validate and normalize diagnosis codes."""
        if not v:
            raise ValueError("At least one diagnosis code is required")
        return [code.strip().upper() for code in v]


class RepricedClaimLine(BaseModel):
    """Represents a repriced claim line with Medicare allowed amount."""

    line_number: int
    procedure_code: str
    modifier: Optional[str]
    place_of_service: str
    locality: str
    units: int

    # Original billed amount (if provided)
    billed_amount: Optional[float] = None

    # Medicare pricing components
    work_rvu: float = Field(..., description="Work Relative Value Unit")
    pe_rvu: float = Field(..., description="Practice Expense RVU")
    mp_rvu: float = Field(..., description="Malpractice RVU")

    work_gpci: float = Field(..., description="Work GPCI")
    pe_gpci: float = Field(..., description="Practice Expense GPCI")
    mp_gpci: float = Field(..., description="Malpractice GPCI")

    conversion_factor: float = Field(..., description="Medicare conversion factor")

    # Calculated amounts
    medicare_allowed: float = Field(..., description="Total Medicare allowed amount")
    adjustment_reason: Optional[str] = Field(
        None,
        description="Reason for any adjustments (e.g., MPPR, modifier)"
    )


class RepricedClaim(BaseModel):
    """Represents a fully repriced claim."""

    claim_id: str
    patient_id: str
    diagnosis_codes: List[str]
    lines: List[RepricedClaimLine]

    # Calculated totals
    total_billed: Optional[float] = Field(None, description="Total billed amount")
    total_allowed: float = Field(..., description="Total Medicare allowed amount")

    # Summary information
    repricing_date: Optional[str] = None
    notes: Optional[List[str]] = Field(default_factory=list)

    def add_note(self, note: str) -> None:
        """Add a note to the repriced claim."""
        if self.notes is None:
            self.notes = []
        self.notes.append(note)
