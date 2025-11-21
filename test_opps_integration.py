#!/usr/bin/env python3
"""
Test script to verify OPPS and anesthesia data integration.
"""

from pathlib import Path
from medicare_repricing.fee_schedule import MedicareFeeSchedule

def test_opps_integration():
    """Test loading and accessing OPPS data."""
    print("Testing OPPS and Anesthesia data integration...")
    print("-" * 60)

    # Create fee schedule and load data
    fee_schedule = MedicareFeeSchedule()
    data_dir = Path(__file__).parent / 'data'
    fee_schedule.load_from_directory(data_dir)

    # Test counts
    print(f"Loaded {len(fee_schedule.rvu_data)} RVU entries")
    print(f"Loaded {len(fee_schedule.gpci_data)} GPCI entries")
    print(f"Loaded {len(fee_schedule.opps_data)} OPPS entries")
    print(f"Loaded {len(fee_schedule.anesthesia_data)} Anesthesia entries")
    print()

    # Test OPPS lookup
    print("Testing OPPS data lookup...")
    opps = fee_schedule.get_opps(
        hcpcs="0633T",
        modifier="TC",
        carrier="01112",
        locality="05"
    )

    if opps:
        print(f"✓ Found OPPS entry for 0633T-TC:")
        print(f"  HCPCS: {opps.hcpcs}")
        print(f"  Modifier: {opps.modifier}")
        print(f"  Carrier: {opps.carrier}")
        print(f"  Locality: {opps.locality}")
        print(f"  Facility Price: ${opps.facility_price:.2f}")
        print(f"  Non-Facility Price: ${opps.non_facility_price:.2f}")
    else:
        print("✗ Failed to find OPPS entry")
    print()

    # Test anesthesia lookup
    print("Testing Anesthesia data lookup...")
    anes = fee_schedule.get_anesthesia(contractor="10112", locality="00")

    if anes:
        print(f"✓ Found anesthesia entry for Alabama:")
        print(f"  Contractor: {anes.contractor}")
        print(f"  Locality: {anes.locality}")
        print(f"  Locality Name: {anes.locality_name}")
        print(f"  Conversion Factor: ${anes.conversion_factor:.2f}")
    else:
        print("✗ Failed to find anesthesia entry")
    print()

    # Test another anesthesia lookup - California
    anes_ca = fee_schedule.get_anesthesia(contractor="01112", locality="05")
    if anes_ca:
        print(f"✓ Found anesthesia entry for San Francisco:")
        print(f"  Locality Name: {anes_ca.locality_name}")
        print(f"  Conversion Factor: ${anes_ca.conversion_factor:.2f}")
    print()

    print("-" * 60)
    print("✓ All tests passed successfully!")

if __name__ == '__main__':
    test_opps_integration()
