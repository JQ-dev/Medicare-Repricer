"""
Data models for Medicare claims and repricing.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ClaimLine(BaseModel):
    """Represents a single line item on a medical claim."""

    line_number: int = Field(..., description="Sequential line number", ge=1)
    procedure_code: str = Field(..., description="CPT or HCPCS procedure code")
    modifiers: Optional[List[str]] = Field(None, description="Procedure modifiers (up to 2, e.g., ['26', 'TC'])", max_length=2)
    place_of_service: str = Field(..., description="Two-digit place of service code")
    locality: Optional[str] = Field(None, description="Medicare locality code for GPCI")
    zip_code: Optional[str] = Field(None, description="Zip code (will be mapped to locality if locality not provided)")
    units: int = Field(1, description="Number of units", ge=1)
    diagnosis_pointers: Optional[List[int]] = Field(
        None,
        description="Pointers to diagnosis codes (1-based index)"
    )

    # Anesthesia-specific fields
    anesthesia_time_minutes: Optional[int] = Field(
        None,
        description="Total anesthesia time in minutes (for calculating time units)",
        ge=0
    )
    physical_status_modifier: Optional[str] = Field(
        None,
        description="Physical status modifier (P1-P6) for anesthesia complexity"
    )
    anesthesia_modifying_units: Optional[int] = Field(
        None,
        description="Additional modifying units (e.g., for qualifying circumstances, age extremes)",
        ge=0
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

    @field_validator('modifiers')
    @classmethod
    def validate_modifiers(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize modifiers."""
        if v is None:
            return None
        if len(v) > 2:
            raise ValueError("Maximum of 2 modifiers allowed")
        # Normalize to uppercase and strip whitespace
        return [m.strip().upper() for m in v if m and m.strip()]


class Claim(BaseModel):
    """Represents a complete medical claim."""

    claim_id: str = Field(..., description="Unique claim identifier")
    lines: List[ClaimLine] = Field(
        ...,
        description="List of claim line items",
        min_length=1
    )


class RepricedClaimLine(BaseModel):
    """Represents a repriced claim line with Medicare allowed amount."""

    line_number: int
    procedure_code: str
    modifiers: Optional[List[str]]
    place_of_service: str
    locality: str
    zip_code: Optional[str] = None
    units: int

    # Original billed amount (if provided)
    billed_amount: Optional[float] = None

    # Service type
    service_type: str = Field(default="PFS", description="Service type: PFS, ANESTHESIA, or OPPS")

    # Standard Medicare pricing components (for PFS/OPPS)
    work_rvu: Optional[float] = Field(None, description="Work Relative Value Unit")
    pe_rvu: Optional[float] = Field(None, description="Practice Expense RVU")
    mp_rvu: Optional[float] = Field(None, description="Malpractice RVU")

    work_gpci: Optional[float] = Field(None, description="Work GPCI")
    pe_gpci: Optional[float] = Field(None, description="Practice Expense GPCI")
    mp_gpci: Optional[float] = Field(None, description="Malpractice GPCI")

    conversion_factor: float = Field(..., description="Medicare conversion factor")

    # Anesthesia-specific pricing components
    anesthesia_base_units: Optional[int] = Field(None, description="Anesthesia base units")
    anesthesia_time_units: Optional[float] = Field(None, description="Anesthesia time units")
    anesthesia_modifying_units: Optional[int] = Field(None, description="Anesthesia modifying units")
    anesthesia_total_units: Optional[float] = Field(None, description="Total anesthesia units")

    # Calculated amounts
    medicare_allowed: float = Field(..., description="Total Medicare allowed amount")
    adjustment_reason: Optional[str] = Field(
        None,
        description="Reason for any adjustments (e.g., MPPR, modifier)"
    )


class RepricedClaim(BaseModel):
    """Represents a fully repriced claim."""

    claim_id: str
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
