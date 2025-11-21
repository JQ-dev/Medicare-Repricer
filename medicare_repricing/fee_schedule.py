"""
Medicare Fee Schedule data structures and management.
"""

from typing import Dict, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class RVUData:
    """Relative Value Unit data for a procedure code."""

    procedure_code: str
    modifier: Optional[str]
    description: str

    # Non-Facility (Office) RVUs
    work_rvu_nf: float
    pe_rvu_nf: float
    mp_rvu_nf: float

    # Facility (Hospital) RVUs
    work_rvu_f: float
    pe_rvu_f: float
    mp_rvu_f: float

    # Multiple procedure indicator
    # 0 = No adjustment, 2 = Standard MPPR (50% for second and subsequent)
    mp_indicator: int = 0


@dataclass
class GPCIData:
    """Geographic Practice Cost Index data for a locality."""

    locality: str
    locality_name: str
    work_gpci: float
    pe_gpci: float
    mp_gpci: float


@dataclass
class OPPSData:
    """Outpatient Prospective Payment System (OPPS) pricing data."""

    hcpcs: str
    modifier: Optional[str]
    status: str
    carrier: str
    locality: str
    facility_price: float
    non_facility_price: float


@dataclass
class AnesthesiaData:
    """Anesthesia conversion factor data by locality."""

    contractor: str
    locality: str
    locality_name: str
    conversion_factor: float


@dataclass
class AnesthesiaBaseUnitData:
    """Anesthesia base unit data for a procedure code."""

    procedure_code: str
    base_units: int
    description: str


@dataclass
class MSDRGData:
    """MS-DRG (Medicare Severity Diagnosis-Related Group) data."""

    ms_drg: str  # MS-DRG code (e.g., "470", "871")
    description: str
    relative_weight: float
    geometric_mean_los: float  # Geometric mean length of stay
    arithmetic_mean_los: float  # Arithmetic mean length of stay


@dataclass
class WageIndexData:
    """Hospital wage index data by CBSA or provider."""

    cbsa_code: str  # Core Based Statistical Area code or provider number
    area_name: str
    wage_index: float  # Operating wage index
    capital_wage_index: Optional[float] = None  # Capital geographic adjustment factor (GAF)


@dataclass
class HospitalData:
    """Hospital-specific data for IPPS adjustments."""

    provider_number: str
    hospital_name: str
    cbsa_code: str
    wage_index: float

    # Teaching hospital data
    is_teaching_hospital: bool = False
    intern_resident_to_bed_ratio: Optional[float] = None  # For IME calculation

    # DSH data
    is_dsh_hospital: bool = False
    dsh_patient_percentage: Optional[float] = None  # DSH adjustment percentage

    # Location
    is_rural: bool = False

    # Other
    bed_count: Optional[int] = None


class MedicareFeeSchedule:
    """
    Medicare Physician Fee Schedule database.

    Manages RVU data and GPCI data for Medicare pricing calculations.
    """

    def __init__(self, conversion_factor: float = 32.35):
        """
        Initialize the fee schedule.

        Args:
            conversion_factor: Medicare conversion factor (2025 value is $32.35)
                              Previous years: 2024=$33.2875, 2023=$33.8872
        """
        self.conversion_factor = conversion_factor
        self.rvu_data: Dict[str, RVUData] = {}
        self.gpci_data: Dict[str, GPCIData] = {}
        self.opps_data: Dict[str, OPPSData] = {}
        self.anesthesia_data: Dict[str, AnesthesiaData] = {}
        self.anesthesia_base_units: Dict[str, AnesthesiaBaseUnitData] = {}

        # IPPS (Inpatient) data
        self.ms_drg_data: Dict[str, MSDRGData] = {}
        self.wage_index_data: Dict[str, WageIndexData] = {}
        self.hospital_data: Dict[str, HospitalData] = {}

        # IPPS standardized amounts (FY 2026)
        self.ipps_operating_standard_amount_high: float = 6690.00  # Wage index > 1
        self.ipps_operating_standard_amount_low: float = 6690.00   # Wage index <= 1
        self.ipps_capital_standard_amount: float = 488.59
        self.ipps_labor_share: float = 0.676  # 67.6% labor-related
        self.ipps_outlier_threshold: float = 46217.00  # Fixed-loss threshold
        self.ipps_outlier_payment_rate: float = 0.80  # 80% of costs above threshold

    def add_rvu(self, rvu: RVUData) -> None:
        """Add RVU data for a procedure code."""
        key = self._make_rvu_key(rvu.procedure_code, rvu.modifier)
        self.rvu_data[key] = rvu

    def add_gpci(self, gpci: GPCIData) -> None:
        """Add GPCI data for a locality."""
        self.gpci_data[gpci.locality] = gpci

    def add_opps(self, opps: OPPSData) -> None:
        """Add OPPS data for a procedure code."""
        key = self._make_opps_key(opps.hcpcs, opps.modifier, opps.carrier, opps.locality)
        self.opps_data[key] = opps

    def add_anesthesia(self, anes: AnesthesiaData) -> None:
        """Add anesthesia conversion factor data for a locality."""
        key = f"{anes.contractor}:{anes.locality}"
        self.anesthesia_data[key] = anes

    def add_anesthesia_base_unit(self, base_unit: AnesthesiaBaseUnitData) -> None:
        """Add anesthesia base unit data for a procedure code."""
        self.anesthesia_base_units[base_unit.procedure_code] = base_unit

    def add_ms_drg(self, ms_drg: MSDRGData) -> None:
        """Add MS-DRG data."""
        self.ms_drg_data[ms_drg.ms_drg] = ms_drg

    def add_wage_index(self, wage_index: WageIndexData) -> None:
        """Add wage index data for a CBSA."""
        self.wage_index_data[wage_index.cbsa_code] = wage_index

    def add_hospital(self, hospital: HospitalData) -> None:
        """Add hospital-specific data."""
        self.hospital_data[hospital.provider_number] = hospital

    def get_rvu(self, procedure_code: str, modifier: Optional[str] = None) -> Optional[RVUData]:
        """
        Get RVU data for a procedure code.

        Args:
            procedure_code: CPT or HCPCS code
            modifier: Optional modifier

        Returns:
            RVUData if found, None otherwise
        """
        # Try with modifier first
        if modifier:
            key = self._make_rvu_key(procedure_code, modifier)
            if key in self.rvu_data:
                return self.rvu_data[key]

        # Fall back to code without modifier
        key = self._make_rvu_key(procedure_code, None)
        return self.rvu_data.get(key)

    def get_gpci(self, locality: str) -> Optional[GPCIData]:
        """
        Get GPCI data for a locality.

        Args:
            locality: Medicare locality code

        Returns:
            GPCIData if found, None otherwise
        """
        return self.gpci_data.get(locality)

    def get_opps(self, hcpcs: str, modifier: Optional[str] = None,
                 carrier: Optional[str] = None, locality: Optional[str] = None) -> Optional[OPPSData]:
        """
        Get OPPS data for a procedure code.

        Args:
            hcpcs: HCPCS procedure code
            modifier: Optional modifier
            carrier: Optional carrier code
            locality: Optional locality code

        Returns:
            OPPSData if found, None otherwise
        """
        # Try with all parameters
        if carrier and locality:
            key = self._make_opps_key(hcpcs, modifier, carrier, locality)
            if key in self.opps_data:
                return self.opps_data[key]

        # Try without modifier
        if carrier and locality:
            key = self._make_opps_key(hcpcs, None, carrier, locality)
            if key in self.opps_data:
                return self.opps_data[key]

        return None

    def get_anesthesia(self, contractor: str, locality: str) -> Optional[AnesthesiaData]:
        """
        Get anesthesia conversion factor for a locality.

        Args:
            contractor: Contractor code
            locality: Medicare locality code

        Returns:
            AnesthesiaData if found, None otherwise
        """
        key = f"{contractor}:{locality}"
        return self.anesthesia_data.get(key)

    def get_anesthesia_base_unit(self, procedure_code: str) -> Optional[AnesthesiaBaseUnitData]:
        """
        Get anesthesia base unit data for a procedure code.

        Args:
            procedure_code: CPT anesthesia code

        Returns:
            AnesthesiaBaseUnitData if found, None otherwise
        """
        return self.anesthesia_base_units.get(procedure_code)

    def get_ms_drg(self, ms_drg: str) -> Optional[MSDRGData]:
        """
        Get MS-DRG data.

        Args:
            ms_drg: MS-DRG code

        Returns:
            MSDRGData if found, None otherwise
        """
        return self.ms_drg_data.get(ms_drg)

    def get_wage_index(self, cbsa_code: str) -> Optional[WageIndexData]:
        """
        Get wage index data for a CBSA.

        Args:
            cbsa_code: CBSA code

        Returns:
            WageIndexData if found, None otherwise
        """
        return self.wage_index_data.get(cbsa_code)

    def get_hospital(self, provider_number: str) -> Optional[HospitalData]:
        """
        Get hospital-specific data.

        Args:
            provider_number: Medicare provider number

        Returns:
            HospitalData if found, None otherwise
        """
        return self.hospital_data.get(provider_number)

    def load_from_directory(self, directory: Path) -> None:
        """
        Load fee schedule data from JSON files in a directory.

        Expected files:
        - rvu_data.json: RVU data
        - gpci_data.json: GPCI data
        - opps_data.json: OPPS data
        - anesthesia_data.json: Anesthesia conversion factors

        Args:
            directory: Path to directory containing data files
        """
        directory = Path(directory)

        # Load RVU data
        rvu_file = directory / "rvu_data.json"
        if rvu_file.exists():
            with open(rvu_file, 'r') as f:
                rvu_list = json.load(f)
                for rvu_dict in rvu_list:
                    rvu = RVUData(**rvu_dict)
                    self.add_rvu(rvu)

        # Load GPCI data
        gpci_file = directory / "gpci_data.json"
        if gpci_file.exists():
            with open(gpci_file, 'r') as f:
                gpci_list = json.load(f)
                for gpci_dict in gpci_list:
                    gpci = GPCIData(**gpci_dict)
                    self.add_gpci(gpci)

        # Load OPPS data
        opps_file = directory / "opps_data.json"
        if opps_file.exists():
            with open(opps_file, 'r') as f:
                opps_list = json.load(f)
                for opps_dict in opps_list:
                    opps = OPPSData(**opps_dict)
                    self.add_opps(opps)

        # Load Anesthesia data
        anes_file = directory / "anesthesia_data.json"
        if anes_file.exists():
            with open(anes_file, 'r') as f:
                anes_list = json.load(f)
                for anes_dict in anes_list:
                    anes = AnesthesiaData(**anes_dict)
                    self.add_anesthesia(anes)

        # Load Anesthesia Base Units
        anes_base_file = directory / "anesthesia_base_units.json"
        if anes_base_file.exists():
            with open(anes_base_file, 'r') as f:
                data = json.load(f)
                # The file has a "base_units" key containing the actual data
                if "base_units" in data:
                    for code, info in data["base_units"].items():
                        base_unit = AnesthesiaBaseUnitData(
                            procedure_code=code,
                            base_units=info["base_units"],
                            description=info["description"]
                        )
                        self.add_anesthesia_base_unit(base_unit)

        # Load MS-DRG data
        ms_drg_file = directory / "ms_drg_data.json"
        if ms_drg_file.exists():
            with open(ms_drg_file, 'r') as f:
                ms_drg_list = json.load(f)
                for ms_drg_dict in ms_drg_list:
                    ms_drg = MSDRGData(**ms_drg_dict)
                    self.add_ms_drg(ms_drg)

        # Load Wage Index data
        wage_index_file = directory / "wage_index_data.json"
        if wage_index_file.exists():
            with open(wage_index_file, 'r') as f:
                wage_index_list = json.load(f)
                for wi_dict in wage_index_list:
                    wi = WageIndexData(**wi_dict)
                    self.add_wage_index(wi)

        # Load Hospital data
        hospital_file = directory / "hospital_data.json"
        if hospital_file.exists():
            with open(hospital_file, 'r') as f:
                hospital_list = json.load(f)
                for hosp_dict in hospital_list:
                    hosp = HospitalData(**hosp_dict)
                    self.add_hospital(hosp)

    @staticmethod
    def _make_rvu_key(procedure_code: str, modifier: Optional[str]) -> str:
        """Create a unique key for RVU lookup."""
        if modifier:
            return f"{procedure_code}:{modifier}"
        return procedure_code

    @staticmethod
    def _make_opps_key(hcpcs: str, modifier: Optional[str],
                       carrier: str, locality: str) -> str:
        """Create a unique key for OPPS lookup."""
        if modifier:
            return f"{hcpcs}:{modifier}:{carrier}:{locality}"
        return f"{hcpcs}::{carrier}:{locality}"


def create_default_fee_schedule() -> MedicareFeeSchedule:
    """
    Create a fee schedule with default sample data.

    This includes commonly used CPT codes with realistic RVU values.
    Uses 2025 Medicare conversion factor.

    Returns:
        MedicareFeeSchedule with sample data loaded
    """
    fee_schedule = MedicareFeeSchedule(conversion_factor=32.35)

    # Add sample RVU data for common procedures
    sample_rvus = [
        # Office Visits - Established Patient
        RVUData("99211", None, "Office visit, established patient, minimal",
                0.18, 0.61, 0.02, 0.18, 0.45, 0.02, 0),
        RVUData("99212", None, "Office visit, established patient, low",
                0.48, 0.98, 0.04, 0.48, 0.73, 0.04, 0),
        RVUData("99213", None, "Office visit, established patient, moderate",
                0.97, 1.57, 0.09, 0.97, 1.18, 0.09, 0),
        RVUData("99214", None, "Office visit, established patient, high",
                1.50, 2.13, 0.14, 1.50, 1.60, 0.14, 0),
        RVUData("99215", None, "Office visit, established patient, comprehensive",
                2.11, 2.80, 0.20, 2.11, 2.10, 0.20, 0),

        # Office Visits - New Patient
        RVUData("99201", None, "Office visit, new patient, minimal",
                0.48, 0.98, 0.04, 0.48, 0.73, 0.04, 0),
        RVUData("99202", None, "Office visit, new patient, low",
                0.93, 1.57, 0.09, 0.93, 1.18, 0.09, 0),
        RVUData("99203", None, "Office visit, new patient, moderate",
                1.42, 2.13, 0.14, 1.42, 1.60, 0.14, 0),
        RVUData("99204", None, "Office visit, new patient, high",
                2.43, 2.94, 0.23, 2.43, 2.20, 0.23, 0),
        RVUData("99205", None, "Office visit, new patient, comprehensive",
                3.17, 3.69, 0.30, 3.17, 2.77, 0.30, 0),

        # Laboratory
        RVUData("80053", None, "Comprehensive metabolic panel",
                0.00, 1.13, 0.05, 0.00, 0.85, 0.05, 0),
        RVUData("85025", None, "Complete blood count (CBC) with differential",
                0.00, 0.85, 0.04, 0.00, 0.64, 0.04, 0),
        RVUData("80061", None, "Lipid panel",
                0.00, 0.92, 0.04, 0.00, 0.69, 0.04, 0),
        RVUData("84443", None, "Thyroid stimulating hormone (TSH)",
                0.00, 0.68, 0.03, 0.00, 0.51, 0.03, 0),

        # Imaging - X-Ray
        RVUData("71045", None, "Chest X-ray, single view",
                0.17, 4.92, 0.15, 0.17, 0.82, 0.15, 2),
        RVUData("71046", None, "Chest X-ray, 2 views",
                0.22, 6.41, 0.19, 0.22, 1.07, 0.19, 2),
        RVUData("73030", None, "Shoulder X-ray, 2 views",
                0.18, 4.25, 0.13, 0.18, 0.71, 0.13, 2),

        # Imaging with modifiers (Professional/Technical components)
        RVUData("71046", "26", "Chest X-ray, 2 views - Professional component",
                0.22, 0.00, 0.19, 0.22, 0.00, 0.19, 0),
        RVUData("71046", "TC", "Chest X-ray, 2 views - Technical component",
                0.00, 6.41, 0.00, 0.00, 1.07, 0.00, 2),

        # Procedures
        RVUData("12001", None, "Simple repair, superficial wounds, 2.5 cm or less",
                1.19, 4.82, 0.23, 1.19, 2.54, 0.23, 2),
        RVUData("12002", None, "Simple repair, superficial wounds, 2.6 to 7.5 cm",
                1.48, 5.67, 0.29, 1.48, 2.99, 0.29, 2),
        RVUData("17000", None, "Destruction, benign or premalignant lesion, first",
                0.76, 2.94, 0.10, 0.76, 1.55, 0.10, 2),
        RVUData("17003", None, "Destruction, benign lesion, each additional",
                0.14, 0.42, 0.02, 0.14, 0.22, 0.02, 2),

        # Injections
        RVUData("96372", None, "Therapeutic injection, subcutaneous or intramuscular",
                0.17, 0.98, 0.03, 0.17, 0.52, 0.03, 0),
        RVUData("20610", None, "Arthrocentesis, major joint",
                1.01, 4.67, 0.25, 1.01, 2.46, 0.25, 2),
    ]

    for rvu in sample_rvus:
        fee_schedule.add_rvu(rvu)

    # Add sample GPCI data for various localities
    sample_gpcis = [
        # New York - Manhattan
        GPCIData("01", "Manhattan, NY", 1.094, 1.385, 1.797),
        # California - Los Angeles
        GPCIData("05", "Los Angeles, CA", 1.037, 1.189, 0.681),
        # Texas - Dallas
        GPCIData("26", "Dallas, TX", 1.003, 0.987, 0.917),
        # Florida - Miami
        GPCIData("03", "Miami, FL", 1.000, 1.038, 2.168),
        # Illinois - Chicago
        GPCIData("16", "Chicago, IL", 1.004, 1.041, 1.306),
        # National average (default)
        GPCIData("00", "National Average", 1.000, 1.000, 1.000),
        # Office setting (default for testing)
        GPCIData("99", "Default/Office", 1.000, 1.000, 1.000),
    ]

    for gpci in sample_gpcis:
        fee_schedule.add_gpci(gpci)

    return fee_schedule
