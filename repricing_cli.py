#!/usr/bin/env python
"""
Command-line interface for Medicare repricing.

Quick tool for repricing individual procedures or claims.
"""

import argparse
import sys
from medicare_repricing import MedicareRepricer, Claim, ClaimLine


def reprice_procedure(args):
    """Reprice a single procedure."""
    repricer = MedicareRepricer()

    # Create a simple claim with one line
    claim = Claim(
        claim_id="CLI-001",
        patient_id="CLI-PAT",
        diagnosis_codes=[args.diagnosis] if args.diagnosis else ["Z00.00"],
        lines=[
            ClaimLine(
                line_number=1,
                procedure_code=args.procedure,
                modifier=args.modifier,
                place_of_service=args.pos,
                locality=args.locality,
                units=args.units
            )
        ]
    )

    try:
        repriced = repricer.reprice_claim(claim)
        line = repriced.lines[0]

        print("\n" + "=" * 60)
        print("MEDICARE REPRICING RESULT")
        print("=" * 60)
        print(f"Procedure Code:  {line.procedure_code}")
        if line.modifier:
            print(f"Modifier:        {line.modifier}")
        print(f"Place of Service: {line.place_of_service}")
        print(f"Locality:        {line.locality}")
        print(f"Units:           {line.units}")
        print()
        print("RVU Values:")
        print(f"  Work RVU:  {line.work_rvu:.4f}")
        print(f"  PE RVU:    {line.pe_rvu:.4f}")
        print(f"  MP RVU:    {line.mp_rvu:.4f}")
        print()
        print("GPCI Values:")
        print(f"  Work GPCI: {line.work_gpci:.4f}")
        print(f"  PE GPCI:   {line.pe_gpci:.4f}")
        print(f"  MP GPCI:   {line.mp_gpci:.4f}")
        print()
        print(f"Conversion Factor: ${line.conversion_factor:.4f}")
        print()
        print(f"MEDICARE ALLOWED:  ${line.medicare_allowed:.2f}")
        print("=" * 60)

        if line.adjustment_reason:
            print(f"\nNotes: {line.adjustment_reason}")

        print()

    except ValueError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


def lookup_procedure(args):
    """Look up procedure information."""
    repricer = MedicareRepricer()

    info = repricer.get_procedure_info(args.procedure, args.modifier)

    if info is None:
        print(f"\nERROR: Procedure code {args.procedure} not found in fee schedule", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("PROCEDURE INFORMATION")
    print("=" * 60)
    print(f"Code:        {info['procedure_code']}")
    if info['modifier']:
        print(f"Modifier:    {info['modifier']}")
    print(f"Description: {info['description']}")
    print()
    print("Non-Facility RVUs:")
    print(f"  Work: {info['work_rvu_non_facility']:.4f}")
    print(f"  PE:   {info['pe_rvu_non_facility']:.4f}")
    print(f"  MP:   {info['mp_rvu_non_facility']:.4f}")
    print()
    print("Facility RVUs:")
    print(f"  Work: {info['work_rvu_facility']:.4f}")
    print(f"  PE:   {info['pe_rvu_facility']:.4f}")
    print(f"  MP:   {info['mp_rvu_facility']:.4f}")
    print()
    print(f"MPPR Indicator: {info['mppr_indicator']}")
    print(f"Conversion Factor: ${info['conversion_factor']:.4f}")
    print("=" * 60)
    print()


def lookup_locality(args):
    """Look up locality information."""
    repricer = MedicareRepricer()

    info = repricer.get_locality_info(args.locality)

    if info is None:
        print(f"\nERROR: Locality {args.locality} not found", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("LOCALITY INFORMATION")
    print("=" * 60)
    print(f"Locality:      {info['locality']}")
    print(f"Name:          {info['locality_name']}")
    print()
    print("GPCI Values:")
    print(f"  Work GPCI: {info['work_gpci']:.4f}")
    print(f"  PE GPCI:   {info['pe_gpci']:.4f}")
    print(f"  MP GPCI:   {info['mp_gpci']:.4f}")
    print("=" * 60)
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Medicare Claims Repricing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reprice an office visit
  %(prog)s reprice 99213 --pos 11 --locality 00

  # Reprice with modifier and multiple units
  %(prog)s reprice 71046 --pos 22 --locality 01 --modifier 26 --units 1

  # Look up procedure information
  %(prog)s lookup-procedure 99214

  # Look up locality information
  %(prog)s lookup-locality 01
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Reprice command
    reprice_parser = subparsers.add_parser('reprice', help='Reprice a procedure')
    reprice_parser.add_argument('procedure', help='CPT/HCPCS procedure code')
    reprice_parser.add_argument('--pos', default='11', help='Place of service (default: 11 - Office)')
    reprice_parser.add_argument('--locality', default='00', help='Medicare locality (default: 00 - National)')
    reprice_parser.add_argument('--modifier', help='Procedure modifier (e.g., 26, TC, 50)')
    reprice_parser.add_argument('--units', type=int, default=1, help='Number of units (default: 1)')
    reprice_parser.add_argument('--diagnosis', help='ICD-10 diagnosis code (default: Z00.00)')
    reprice_parser.set_defaults(func=reprice_procedure)

    # Lookup procedure command
    lookup_proc_parser = subparsers.add_parser('lookup-procedure', help='Look up procedure information')
    lookup_proc_parser.add_argument('procedure', help='CPT/HCPCS procedure code')
    lookup_proc_parser.add_argument('--modifier', help='Procedure modifier')
    lookup_proc_parser.set_defaults(func=lookup_procedure)

    # Lookup locality command
    lookup_loc_parser = subparsers.add_parser('lookup-locality', help='Look up locality information')
    lookup_loc_parser.add_argument('locality', help='Medicare locality code')
    lookup_loc_parser.set_defaults(func=lookup_locality)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
