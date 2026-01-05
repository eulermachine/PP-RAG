#!/usr/bin/env python3
"""
03_bench_retrieve2.py
Variant 2: Retrieve Phase Benchmark with Communication Tracking
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner2 import BenchmarkRunner2


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Retrieve Phase (Variant 2)")
    print("="*60)
    
    runner = BenchmarkRunner2("./config/config2.yaml")
    vectors = runner.load_data()
    
    # Build index first
    print("\n[Prerequisite] Building index first...")
    runner.benchmark_setup(vectors)
    
    # Run retrieval tests
    results = runner.benchmark_retrieve(vectors)
    
    # Print summary
    print("\n" + "="*60)
    print("Retrieve Phase Summary (Variant 2)")
    print("="*60)
    
    for r in results:
        if 'search' in r.operation:
            print(f"\n{r.operation}:")
            print(f"  Total Time: {r.total_time:.4f}s")
            print(f"  Avg per query: {r.avg_time_per_item*1000:.4f}ms")
            if r.communication_bytes > 0:
                print(f"  Communication: {r.communication_bytes / (1024*1024):.2f} MB")
                print(f"  Comm per query: {r.communication_bytes / r.num_items / (1024):.2f} KB")
    
    runner.results.save("./results/retrieve_timings2.json")


if __name__ == "__main__":
    main()
