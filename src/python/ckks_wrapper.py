"""
ckks_wrapper.py
High-level Wrapper for Real CKKS C++ Module
"""
import sys
import numpy as np
from typing import List, Optional

try:
    import pprag_core
except ImportError:
    print("CRITICAL ERROR: 'pprag_core' C++ module not found.")
    print("Please compile the C++ extension:")
    print("  mkdir build && cd build")
    print("  cmake .. -DCMAKE_BUILD_TYPE=Release")
    print("  cmake --build . --config Release")
    raise RuntimeError("Missing required C++ module: pprag_core")

class HEContext:
    def __init__(self, config: dict):
        enc_config = config.get('encryption', {})
        # Extract CKKS parameters from config
        poly_modulus_degree = enc_config.get('poly_modulus_degree', 8192)
        scale_power = enc_config.get('scale_power', 40)
        scale = 2.0 ** scale_power
        
        # Initialize CKKS context with configured parameters
        self.ctx = pprag_core.CKKSContext(poly_modulus_degree, scale)
        print(f"[HE] Initialized CKKS Context (slots={self.ctx.slot_count()})")
        
    def encrypt(self, vector: np.ndarray):
        """Encrypt a numpy vector"""
        # Ensure vector is float64
        vec = vector.astype(np.float64)
        if vec.ndim == 1:
            return self.ctx.encrypt_vector(vec)
        else:
            raise ValueError("Only 1D vectors supported for single encryption")
            
    def encrypt_batch(self, vectors: np.ndarray):
        """Encrypt multiple vectors"""
        return [self.encrypt(v) for v in vectors]
        
    def decrypt(self, ciphertext) -> np.ndarray:
        """Decrypt to numpy vector"""
        return self.ctx.decrypt_vector(ciphertext)

class SecureHNSWWrapper:
    def __init__(self, he_ctx: HEContext, config: dict):
        index_config = config.get('index', {})
        M = index_config.get('hnsw_m', 16)
        ef_c = index_config.get('hnsw_ef_construction', 200)
        ef_s = index_config.get('hnsw_ef_search', 100)
        
        self.hnsw = pprag_core.SecureHNSWEncrypted(he_ctx.ctx, M, ef_c, ef_s)
        self.he_ctx = he_ctx
        
    def build_index(self, vectors: np.ndarray):
        """Build index from plaintext vectors (encrypts them internally)"""
        print(f"[HNSW] Building Encrypted Index for {len(vectors)} vectors...")
        # Since our C++ SecureHNSWEncrypted stores ciphertexts, we need to encrypt and add them
        # Note: "build" usually implies batch. We can iterate.
        
        # We assume vectors are plaintext here and we encrypt them one by one to add
        # Alternatively, we could parallelize encryption in Python
        
        for i, vec in enumerate(vectors):
            enc_vec = self.he_ctx.encrypt(vec)
            # Default level 0 for now, or use random level logic within C++?
            # Our C++ implementation of add_encrypted_node expects 'level'. 
            # The random level generation should ideally be inside the class or exposed.
            # But add_encrypted_node logic in my C++ code:
            # "if (id >= node_vectors_.size())... nodes_[id].level = level"
            # It seems the caller must decide the level.
            # We need a random level generator here similar to HNSW standard.
            
            level = self._random_level()
            self.hnsw.add_encrypted_node(i, enc_vec, level)
            
            if (i+1) % 100 == 0:
                print(f"[HNSW] Indexed {i+1}/{len(vectors)}", end='\r')
        print(f"\n[HNSW] Build complete.")
        return [] # Timings?
        
    def search(self, query: np.ndarray, k: int = 10):
        # Encrypt query
        q_enc = self.he_ctx.encrypt(query)
        # Search
        return self.hnsw.search(q_enc, k)
        
    def _random_level(self):
        # Simple Python random level generator
        # M_ is 16 usually. mult = 1/log(M)
        import math
        import random
        mult = 1.0 / math.log(16)
        level = 0
        while random.random() < math.exp(-mult) and level < 16:
            level += 1
        return level

