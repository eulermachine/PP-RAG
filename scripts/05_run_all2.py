#!/usr/bin/env python3
"""
05_run_all2.py
Variant 2: Complete Benchmark Suite (1000 vectors)
Includes setup, retrieval, update phases with communication tracking
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner2 import BenchmarkRunner2
from src.python.visualizer import generate_all_figures


def main():
    print("="*70)
    print("PP-RAG HE Component Benchmark - Variant 2 (Full Suite)")
    print("Hybrid with Partial Client Decryption - Communication Tracking")
    print("="*70)
    
    # Create config specifically for 1000 vectors
    config_path = "./config/config2.yaml"
    
    # Initialize runner
    runner = BenchmarkRunner2(config_path)
    
    # Load data
    vectors = runner.load_data()
    print(f"\n[Config] Testing with {len(vectors)} vectors")
    
    # Phase 1: Setup
    print("\n" + "="*70)
    print("PHASE 1: Setup (Index Building)")
    print("="*70)
    runner.benchmark_setup(vectors)
    
    # Phase 2: Retrieve
    print("\n" + "="*70)
    print("PHASE 2: Retrieve (Query Search)")
    print("="*70)
    runner.benchmark_retrieve(vectors)
    
    # Phase 3: Update
    print("\n" + "="*70)
    print("PHASE 3: Update (Vector Insertion)")
    print("="*70)
    runner.benchmark_update(vectors)
    
    # Save all results
    output_path = "./results/timings2.json"
    runner.results.save(output_path)
    
    # Print summary
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY - Variant 2")
    print("="*70)
    
    print("\n[Setup Results]")
    for r in runner.results.setup_results:
        print(f"  {r.component}/{r.operation}: {r.total_time:.4f}s")
    
    print("\n[Retrieve Results]")
    for r in runner.results.retrieve_results:
        if r.communication_bytes > 0:
            print(f"  {r.component}/{r.operation}: {r.total_time:.4f}s")
            print(f"    └─ Communication: {r.communication_bytes / (1024*1024):.2f} MB")
        else:
            print(f"  {r.component}/{r.operation}: {r.total_time:.4f}s")
    
    print("\n[Update Results]")
    for r in runner.results.update_results:
        print(f"  {r.component}/{r.operation}: {r.total_time:.4f}s")
    
    print("\n" + "="*70)
    print("All benchmarks complete!")
    print(f"Results saved to: {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
