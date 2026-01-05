#!/usr/bin/env python3
"""
04_bench_update2.py
Variant 2: Update Phase Benchmark
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner2 import BenchmarkRunner2


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Update Phase (Variant 2)")
    print("="*60)
    
    runner = BenchmarkRunner2("./config/config2.yaml")
    vectors = runner.load_data()
    
    # Build index first
    print("\n[Prerequisite] Building index first...")
    runner.benchmark_setup(vectors)
    
    # Run update tests
    results = runner.benchmark_update(vectors)
    
    # Print summary
    print("\n" + "="*60)
    print("Update Phase Summary (Variant 2)")
    print("="*60)
    
    for r in results:
        if 'insert' in r.operation:
            print(f"\n{r.operation}:")
            print(f"  Total Time: {r.total_time:.4f}s")
            print(f"  Avg per item: {r.avg_time_per_item*1000:.4f}ms")
    
    runner.results.save("./results/update_timings2.json")


if __name__ == "__main__":
    main()
