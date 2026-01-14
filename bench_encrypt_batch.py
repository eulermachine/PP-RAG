#!/usr/bin/env python3
"""
bench_encrypt_batch.py
Performance sampling script: test parallel performance of `encrypt_batch`
using the Python `ThreadPoolExecutor` layer.
"""
import sys
from pathlib import Path
import numpy as np
from pyinstrument import Profiler

sys.path.insert(0, str(Path(__file__).parent))

from src.python.ckks_wrapper import HEContext
from src.python.data_generator import load_config, load_dataset, get_sample_dataset

def main():
    # Load config and data
    config = load_config("./config/config.yaml")
    full_vectors = load_dataset("./data/vectors_100k_256d.npy")
    
    # Sample a small subset (1000)
    vectors = get_sample_dataset(full_vectors, 1000)
    print(f"Testing encrypt_batch with {len(vectors)} vectors")
    
    # Initialize HE context
    he_ctx = HEContext(config)
    
    # Start profiling
    profiler = Profiler()
    profiler.start()
    
    # Run encrypt_batch (should be parallelized with ThreadPoolExecutor)
    print("Running encrypt_batch (parallel with ThreadPoolExecutor)...")
    encrypted = he_ctx.encrypt_batch(vectors)
    
    profiler.stop()
    
    # Print report
    print("\n" + "="*70)
    print("PROFILING REPORT: encrypt_batch (Python ThreadPoolExecutor)")
    print("="*70 + "\n")
    print(profiler.output_text(unicode=True, color=True, show_all=True))
    
    print(f"\nTotal encrypted vectors: {len(encrypted)}")
    print(f"Success: No errors, all vectors encrypted")

if __name__ == "__main__":
    main()
