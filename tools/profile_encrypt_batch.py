#!/usr/bin/env python3
"""
Small runner to exercise encrypt_batch for profiling.
Will generate random vectors and call the Python wrapper encrypt_batch.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from src.python.ckks_wrapper import HEContext, SecureHNSWWrapper
from src.python.data_generator import load_config

cfg = load_config('config/config.yaml')
# Create HE context
he = HEContext(cfg)
# Create some random vectors matching dataset dimension
dim = cfg['dataset']['dimension']
# Batch size chosen to be moderately large but quick
batch_size = int(os.environ.get('PROFILE_BATCH', '128'))
print(f"Running encrypt_batch with batch_size={batch_size}, dim={dim}")
vecs = np.random.randn(batch_size, dim).astype(np.float64)

# Call encrypt_batch and time
import time
start = time.time()
cts = he.encrypt_batch(vecs)
end = time.time()
print(f"Encryption produced {len(cts)} ciphertexts in {end-start:.4f}s")

# Basic decrypt-verify for first element (if decryption available)
try:
    dec = he.decrypt(cts[0])
    print(f"Decrypted length: {len(dec)}")
except Exception as e:
    print(f"Decryption check skipped or failed: {e}")
