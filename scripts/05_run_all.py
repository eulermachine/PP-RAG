#!/usr/bin/env python3
"""
05_run_all.py
Run the full benchmark suite and generate visualizations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner import run_benchmark
from src.python.visualizer import generate_all_figures


def main():
    print("="*70)
    print("PP-RAG HE Component Benchmark - Full Suite")
    print("="*70)
    
    # Run the full benchmark
    results = run_benchmark("./config/config.yaml")

    # Generate visualizations
    generate_all_figures("./results/timings.json", "./results/figures")
    
    print("\n" + "="*70)
    print("All benchmarks and visualizations complete!")
    print("="*70)
    print("\nOutput files:")
    print("  - results/timings.json")
    print("  - results/figures/setup_breakdown.png")
    print("  - results/figures/retrieval_latency_vs_topk.png")
    print("  - results/figures/update_throughput.png")
    print("  - results/figures/component_details.png")


if __name__ == "__main__":
    main()
