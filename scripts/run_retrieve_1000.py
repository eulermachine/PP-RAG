#!/usr/bin/env python3
"""
Run retrieve benchmark with 1000 queries and save results.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner import BenchmarkRunner


def main():
    runner = BenchmarkRunner("./config/config.yaml")
    vectors = runner.load_data()
    print("\n[Prerequisite] Building index first...")
    runner.benchmark_setup(vectors)
    print("\n[Running] Retrieve benchmark for 1000 queries...")
    runner.benchmark_retrieve(vectors, num_queries=1000)
    runner.results.save("./results/retrieve_timings_1000.json")


if __name__ == '__main__':
    main()
