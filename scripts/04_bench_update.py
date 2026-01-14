#!/usr/bin/env python3
"""
04_bench_update.py
Benchmark the Update phase: secure inserts and deletes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner import BenchmarkRunner


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Update Phase")
    print("="*60)
    
    runner = BenchmarkRunner("./config/config.yaml")
    vectors = runner.load_data()
    
    # Prerequisite: build the index first
    print("\n[Prerequisite] Building index first...")
    runner.benchmark_setup(vectors)

    # Run update tests
    results = runner.benchmark_update(vectors)
    
    # Print summary
    print("\n" + "="*60)
    print("Update Phase Summary")
    print("="*60)
    
    for r in results:
        print(f"\n{r.operation}:")
        print(f"  Total: {r.total_time:.4f}s")
        print(f"  Avg per vector: {r.avg_time_per_item*1000:.4f}ms")
        print(f"  Throughput: {r.num_items/r.total_time:.2f} vectors/sec")
    
    runner.results.save("./results/update_timings.json")


if __name__ == "__main__":
    main()
