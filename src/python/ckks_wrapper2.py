"""
ckks_wrapper2.py
High-level Wrapper for Variant 2 CKKS C++ Module
"""
import sys
import os
import numpy as np
from typing import List, Optional

# Add current directory and parent directory to path for importing compiled modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

# Import pprag_core for base classes (CKKSContext, Ciphertext)
try:
    import pprag_core
    print("[HE] Using pprag_core module for base classes")
except ImportError:
    print("ERROR: pprag_core not found, needed for CKKSContext")
    raise

# Import pprag_core2 for variant 2 implementation (SecureHNSWEncrypted2)
try:
    import pprag_core2
    print("[HE] Using pprag_core2 module for SecureHNSWEncrypted2")
except ImportError:
    print("ERROR: pprag_core2 not found, needed for SecureHNSWEncrypted2")
    raise

class HEContext2:
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

class SecureHNSWWrapper2:
    """
    Variant 2: Hybrid HNSW with Partial Client-Side Decryption
    
    Features:
    - Server computes ALL distance operations homomorphically
    - Client decrypts intermediate encrypted distances for layer traversal
    - Communication cost tracking (encrypted distances sent to client)
    - Client makes navigation decisions based on decrypted intermediates
    """
    def __init__(self, he_ctx: HEContext2, config: dict):
        index_config = config.get('index', {})
        M = index_config.get('hnsw_m', 16)
        ef_c = index_config.get('hnsw_ef_construction', 200)
        ef_s = index_config.get('hnsw_ef_search', 100)
        
        # Use SecureHNSWEncrypted2 from pprag_core2
        if hasattr(pprag_core2, 'SecureHNSWEncrypted2'):
            self.hnsw = pprag_core2.SecureHNSWEncrypted2(he_ctx.ctx, M, ef_c, ef_s)
        else:
            # Fallback to original if variant 2 not available
            print("[WARNING] SecureHNSWEncrypted2 not found, using fallback")
            self.hnsw = pprag_core.SecureHNSWEncrypted(he_ctx.ctx, M, ef_c, ef_s)
        
        self.he_ctx = he_ctx
        
    def build_index(self, vectors: np.ndarray):
        """Build index from plaintext vectors (encrypts them internally)"""
        print(f"[HNSW2] Building Encrypted Index for {len(vectors)} vectors...")
        
        for i, vec in enumerate(vectors):
            enc_vec = self.he_ctx.encrypt(vec)
            level = self._random_level()
            self.hnsw.add_encrypted_node(i, enc_vec, level)
            
            if (i+1) % 100 == 0:
                print(f"[HNSW2] Indexed {i+1}/{len(vectors)}", end='\r')
        print(f"\n[HNSW2] Build complete.")
        return [] # Timings?
        
    def search(self, query: np.ndarray, k: int = 10):
        """Search encrypted index"""
        # Encrypt query
        q_enc = self.he_ctx.encrypt(query)
        # Search
        return self.hnsw.search(q_enc, k)
    
    def get_communication_bytes(self) -> int:
        """Get total communication overhead in bytes"""
        if hasattr(self.hnsw, 'get_communication_bytes'):
            return self.hnsw.get_communication_bytes()
        return 0
    
    def reset_communication_counter(self):
        """Reset communication counter"""
        if hasattr(self.hnsw, 'reset_communication_counter'):
            self.hnsw.reset_communication_counter()
        
    def _random_level(self):
        # Simple Python random level generator
        import math
        import random
        mult = 1.0 / math.log(16)
        level = 0
        while random.random() < math.exp(-mult) and level < 16:
            level += 1
        return level
