#!/usr/bin/env python3
"""
02_bench_setup2.py
Variant 2: Setup Phase Benchmark with Communication Tracking
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner2 import BenchmarkRunner2


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Setup Phase (Variant 2)")
    print("="*60)
    
    runner = BenchmarkRunner2("./config/config2.yaml")
    vectors = runner.load_data()
    
    results = runner.benchmark_setup(vectors)
    
    # Print summary
    print("\n" + "="*60)
    print("Setup Phase Summary (Variant 2)")
    print("="*60)
    
    total_time = sum(r.total_time for r in results)
    print(f"\nTotal Setup Time: {total_time:.4f} seconds")
    print("\nBreakdown:")
    for r in results:
        pct = r.total_time / total_time * 100
        print(f"  - {r.component}/{r.operation}: {r.total_time:.4f}s ({pct:.1f}%)")
    
    # Save results
    runner.results.save("./results/setup_timings2.json")


if __name__ == "__main__":
    main()
