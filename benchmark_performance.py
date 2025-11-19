"""
Performance benchmark for Medicare repricing system.

Tests processing speed with various claim volumes and identifies bottlenecks.
"""

import time
import random
from typing import List
from medicare_repricing import MedicareRepricer, Claim, ClaimLine


def generate_test_claims(num_claims: int, lines_per_claim: int = 3) -> List[Claim]:
    """Generate random test claims for benchmarking."""
    procedure_codes = ["99213", "99214", "99215", "80053", "85025", "71046", "12001", "12002"]
    diagnosis_codes = ["I10", "E11.9", "M25.511", "S61.001A", "R05.9"]
    localities = ["00", "01", "05", "26", "03"]
    pos_codes = ["11", "22"]

    claims = []
    for i in range(num_claims):
        lines = []
        for j in range(lines_per_claim):
            lines.append(ClaimLine(
                line_number=j + 1,
                procedure_code=random.choice(procedure_codes),
                modifier=None,
                place_of_service=random.choice(pos_codes),
                locality=random.choice(localities),
                units=1
            ))

        claim = Claim(
            claim_id=f"BENCH{i:06d}",
            patient_id=f"PAT{i:06d}",
            diagnosis_codes=random.sample(diagnosis_codes, k=random.randint(1, 3)),
            lines=lines
        )
        claims.append(claim)

    return claims


def benchmark_sequential_processing():
    """Benchmark the current sequential processing approach."""
    print("=" * 70)
    print("MEDICARE REPRICING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print()

    repricer = MedicareRepricer()

    # Test with increasing volumes
    test_sizes = [10, 100, 1000, 5000]

    for num_claims in test_sizes:
        print(f"Testing {num_claims:,} claims with 3 lines each ({num_claims * 3:,} total lines)...")

        # Generate test data
        claims = generate_test_claims(num_claims, lines_per_claim=3)

        # Time the repricing
        start_time = time.time()
        repriced_claims = repricer.reprice_claims(claims)
        end_time = time.time()

        elapsed = end_time - start_time
        claims_per_sec = num_claims / elapsed if elapsed > 0 else 0
        lines_per_sec = (num_claims * 3) / elapsed if elapsed > 0 else 0

        print(f"  Time:          {elapsed:.3f} seconds")
        print(f"  Throughput:    {claims_per_sec:.1f} claims/sec")
        print(f"  Lines/sec:     {lines_per_sec:.1f} lines/sec")
        print(f"  Avg per claim: {(elapsed/num_claims)*1000:.2f} ms")
        print()

    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    print("Current implementation characteristics:")
    print("  ✓ Fast dictionary lookups (O(1)) for RVU and GPCI data")
    print("  ✓ Simple mathematical calculations")
    print("  ✓ No external dependencies or I/O")
    print()
    print("Potential bottlenecks:")
    print("  ⚠ Sequential processing (no parallelization)")
    print("  ⚠ Pydantic model validation overhead on every object creation")
    print("  ⚠ MPPR procedure identification runs for each claim")
    print("  ⚠ List comprehensions and sorting for MPPR ranking")
    print("  ⚠ No result caching for identical procedure/locality combinations")
    print()
    print("Recommendations for high-volume processing (10K+ claims):")
    print("  1. Add parallel processing with multiprocessing/concurrent.futures")
    print("  2. Implement result caching for common procedure/locality pairs")
    print("  3. Use batch processing with chunking")
    print("  4. Consider NumPy/Pandas for vectorized calculations")
    print("  5. Optional: lazy validation or dataclasses instead of Pydantic")
    print()


def profile_single_claim():
    """Profile a single claim to identify specific bottlenecks."""
    import cProfile
    import pstats
    from io import StringIO

    print("=" * 70)
    print("PROFILING SINGLE CLAIM REPRICING")
    print("=" * 70)
    print()

    repricer = MedicareRepricer()
    claims = generate_test_claims(100, lines_per_claim=5)

    # Profile the repricing
    profiler = cProfile.Profile()
    profiler.enable()

    for claim in claims:
        repricer.reprice_claim(claim)

    profiler.disable()

    # Print statistics
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    print(stream.getvalue())
    print()


def estimate_production_capacity():
    """Estimate production capacity."""
    print("=" * 70)
    print("PRODUCTION CAPACITY ESTIMATE")
    print("=" * 70)
    print()

    repricer = MedicareRepricer()

    # Quick benchmark with 1000 claims
    claims = generate_test_claims(1000, lines_per_claim=3)
    start = time.time()
    repricer.reprice_claims(claims)
    elapsed = time.time() - start

    rate_per_sec = 1000 / elapsed

    print(f"Measured throughput: {rate_per_sec:.1f} claims/second")
    print()
    print("Estimated capacity (single-threaded):")
    print(f"  1 minute:   {rate_per_sec * 60:>10,.0f} claims")
    print(f"  1 hour:     {rate_per_sec * 3600:>10,.0f} claims")
    print(f"  8 hours:    {rate_per_sec * 3600 * 8:>10,.0f} claims")
    print(f"  24 hours:   {rate_per_sec * 3600 * 24:>10,.0f} claims")
    print()
    print("With 4-core parallel processing (estimated):")
    parallel_rate = rate_per_sec * 3.5  # ~87.5% efficiency
    print(f"  1 minute:   {parallel_rate * 60:>10,.0f} claims")
    print(f"  1 hour:     {parallel_rate * 3600:>10,.0f} claims")
    print(f"  8 hours:    {parallel_rate * 3600 * 8:>10,.0f} claims")
    print(f"  24 hours:   {parallel_rate * 3600 * 24:>10,.0f} claims")
    print()
    print("VERDICT:")
    if rate_per_sec > 500:
        print("  ✓ Good for moderate volumes (< 50K claims/day)")
        print("  ⚠ Needs optimization for high volumes (> 100K claims/day)")
    else:
        print("  ⚠ May be slow for production use")
        print("  ⚡ Recommend optimization for volumes > 10K claims/day")
    print()


if __name__ == "__main__":
    random.seed(42)  # For reproducible benchmarks

    benchmark_sequential_processing()
    estimate_production_capacity()

    # Uncomment to run detailed profiling
    # profile_single_claim()
