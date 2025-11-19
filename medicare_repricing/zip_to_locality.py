"""
Zip code to Medicare locality mapping.

This module provides mapping from US zip codes to Medicare locality codes
for Geographic Practice Cost Index (GPCI) lookup.
"""

from typing import Optional, Dict

# Zip code to locality mapping
# This is a sample mapping - in production, this would be a comprehensive database
# covering all US zip codes to their corresponding Medicare localities
#
# Medicare localities are typically organized by state and region.
# Example localities:
# - "00": National average
# - "01": Manhattan, NY
# - "02": NYC suburbs/rest of NY
# - "13": Rest of California
# - "18": Los Angeles, CA
# - "99": Rest of US

# Sample mapping for demonstration
# Format: zip_code_prefix -> locality_code
ZIP_TO_LOCALITY: Dict[str, str] = {
    # New York
    "100": "01",  # Manhattan
    "101": "01",
    "102": "01",
    "103": "02",  # NYC suburbs
    "104": "02",
    "105": "02",
    "110": "02",
    "111": "02",
    "112": "02",
    "113": "02",
    "114": "02",
    "115": "02",
    "116": "02",

    # California - Los Angeles area
    "900": "18",
    "901": "18",
    "902": "18",
    "903": "18",
    "904": "18",
    "905": "18",
    "906": "18",
    "907": "18",

    # California - Rest of state
    "910": "13",
    "911": "13",
    "912": "13",
    "913": "13",
    "914": "13",
    "915": "13",
    "916": "13",
    "917": "13",
    "918": "13",
    "919": "13",
    "920": "13",
    "921": "13",

    # Texas - sample
    "750": "23",
    "751": "23",
    "752": "23",
    "753": "23",
    "754": "23",
    "755": "23",

    # Florida - sample
    "320": "03",
    "321": "03",
    "322": "03",
    "323": "03",
    "324": "03",
    "325": "03",
    "326": "03",
    "327": "03",
    "328": "03",
    "329": "03",
    "330": "03",
    "331": "03",
    "332": "03",
    "333": "03",
    "334": "03",

    # Illinois - Chicago area
    "600": "16",
    "601": "16",
    "602": "16",
    "603": "16",
    "604": "16",
    "605": "16",
    "606": "16",
    "607": "16",
    "608": "16",

    # Pennsylvania
    "150": "42",
    "151": "42",
    "152": "42",
    "153": "42",
    "154": "42",
    "155": "42",
    "156": "42",

    # Massachusetts
    "010": "24",
    "011": "24",
    "012": "24",
    "013": "24",
    "014": "24",
    "015": "24",
    "016": "24",
    "017": "24",
    "018": "24",
    "019": "24",
    "020": "24",
    "021": "24",
    "022": "24",
    "023": "24",
    "024": "24",
    "025": "24",
    "026": "24",
    "027": "24",
}


def get_locality_from_zip(zip_code: str) -> Optional[str]:
    """
    Get Medicare locality code from a zip code.

    This function maps a US zip code to its corresponding Medicare locality
    code for GPCI (Geographic Practice Cost Index) lookup.

    Args:
        zip_code: 5-digit US zip code (can include -4 extension, which is ignored)

    Returns:
        Medicare locality code (e.g., "01", "18", "23"), or None if not found

    Examples:
        >>> get_locality_from_zip("10001")  # Manhattan
        "01"
        >>> get_locality_from_zip("90210")  # Beverly Hills, CA
        "18"
        >>> get_locality_from_zip("60601")  # Chicago, IL
        "16"
    """
    if not zip_code:
        return None

    # Strip whitespace and handle zip+4 format
    zip_code = zip_code.strip().split("-")[0]

    # Validate format
    if not zip_code.isdigit() or len(zip_code) != 5:
        return None

    # Try matching with 3-digit prefix (most common)
    prefix_3 = zip_code[:3]
    if prefix_3 in ZIP_TO_LOCALITY:
        return ZIP_TO_LOCALITY[prefix_3]

    # Try matching with 2-digit prefix (for broader regions)
    prefix_2 = zip_code[:2]
    if prefix_2 in ZIP_TO_LOCALITY:
        return ZIP_TO_LOCALITY[prefix_2]

    # Return national average if no specific mapping found
    # In production, you might want to raise an error instead
    return "00"


def add_zip_mapping(zip_prefix: str, locality: str) -> None:
    """
    Add a new zip code prefix to locality mapping.

    This function allows dynamic addition of zip code mappings at runtime.

    Args:
        zip_prefix: 2 or 3 digit zip code prefix
        locality: Medicare locality code

    Example:
        >>> add_zip_mapping("940", "26")  # Add San Francisco area
    """
    ZIP_TO_LOCALITY[zip_prefix] = locality


def load_zip_mappings_from_file(file_path: str) -> None:
    """
    Load zip code to locality mappings from a CSV file.

    Expected CSV format:
    zip_prefix,locality_code
    100,01
    900,18
    ...

    Args:
        file_path: Path to CSV file containing mappings
    """
    import csv

    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zip_prefix = row["zip_prefix"].strip()
            locality = row["locality_code"].strip()
            ZIP_TO_LOCALITY[zip_prefix] = locality


def get_all_localities() -> set:
    """
    Get set of all locality codes in the mapping.

    Returns:
        Set of all unique locality codes
    """
    return set(ZIP_TO_LOCALITY.values())
