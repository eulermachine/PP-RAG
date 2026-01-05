"""
Benchmark Runner using Real CKKS - Variant 2
Tracks communication overhead (encrypted distances transmitted)
"""
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .data_generator import (
    load_config, load_dataset, get_sample_dataset,
    generate_query_vectors, generate_update_vectors
)
from .ckks_wrapper2 import HEContext2, SecureHNSWWrapper2


@dataclass
class TimingResult:
    """Single operation timing result"""
    component: str
    operation: str
    total_time: float
    num_items: int
    avg_time_per_item: float
    communication_bytes: int = 0  # NEW: Communication overhead in bytes
    details: Dict[str, float] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        if self.details is None:
            result['details'] = {}
        return result


@dataclass
class BenchmarkResult:
    """Full benchmark results"""
    timestamp: str
    config: dict
    setup_results: List[TimingResult]
    retrieve_results: List[TimingResult]
    update_results: List[TimingResult]
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'config': self.config,
            'setup': [r.to_dict() for r in self.setup_results],
            'retrieve': [r.to_dict() for r in self.retrieve_results],
            'update': [r.to_dict() for r in self.update_results]
        }
    
    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"[BenchmarkRunner2] Results saved to {path}")


class BenchmarkRunner2:
    """
    Coordinates Real CKKS Benchmarks - Variant 2
    Tracks communication overhead and partial decryption costs
    """
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        
        # Initialize HE Context - Variant 2
        print("\n[Init] Initializing CKKS Context (Variant 2)...")
        self.he_ctx = HEContext2(self.config)
        
        # Initialize HNSW Wrapper - Variant 2
        self.hnsw = SecureHNSWWrapper2(self.he_ctx, self.config)
        
        self.results = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            config=self.config,
            setup_results=[],
            retrieve_results=[],
            update_results=[]
        )
    
    def load_data(self) -> np.ndarray:
        """Load dataset (support sampling)"""
        data_path = self.config['dataset']['output_path']
        full_data = load_dataset(data_path)
        
        if self.config['benchmark'].get('use_sample', False):
            sample_size = self.config['dataset'].get('sample_size', 1000)
            data = get_sample_dataset(full_data, sample_size)
            print(f"[BenchmarkRunner2] Using sample mode: {len(data)} vectors")
        else:
            data = full_data
            print(f"[BenchmarkRunner2] Using full dataset: {len(data)} vectors")
        
        return data
    
    # ==================== Setup Phase ====================
    
    def benchmark_setup(self, vectors: np.ndarray) -> List[TimingResult]:
        """Test Setup Phase"""
        results = []
        n = len(vectors)
        print(f"\n{'='*60}")
        print(f"[Setup Benchmark V2] Testing with {n} vectors")
        print(f"{'='*60}")
        
        # 1. Encryption Estimation
        print("\n[1/2] Benchmarking encryption throughput...")
        sample_n = min(n, 50)
        t_enc_start = time.perf_counter()
        _ = self.he_ctx.encrypt_batch(vectors[:sample_n])
        t_enc_end = time.perf_counter()
        avg_enc_time = (t_enc_end - t_enc_start) / sample_n
        
        estimated_enc_total = avg_enc_time * n
        results.append(TimingResult(
            component='encryption',
            operation='encrypt_estimate',
            total_time=estimated_enc_total,
            num_items=n,
            avg_time_per_item=avg_enc_time,
            communication_bytes=0
        ))
        print(f"      Avg Encrypt: {avg_enc_time*1000:.4f}ms/vector")
        print(f"      Est Total Encrypt: {estimated_enc_total:.4f}s")
        
        # 2. Secure HNSW Setup (Variant 2)
        print("\n[2/2] Building Encrypted HNSW Index (Variant 2)...")
        t0 = time.perf_counter()
        _ = self.hnsw.build_index(vectors)
        build_time = time.perf_counter() - t0
        
        # No communication cost during index building (local operation)
        results.append(TimingResult(
            component='secure_hnsw2',
            operation='build_index_e2e',
            total_time=build_time,
            num_items=n,
            avg_time_per_item=build_time / n,
            communication_bytes=0
        ))
        print(f"      Total Build Time: {build_time:.4f}s")
        
        self.results.setup_results = results
        return results
    
    # ==================== Retrieve Phase ====================
    
    def benchmark_retrieve(self, vectors: np.ndarray, num_queries: int = None, top_k_values: List[int] = None) -> List[TimingResult]:
        """Test Retrieve Phase with communication tracking"""
        if num_queries is None:
            num_queries = self.config['benchmark'].get('num_test_queries', 50)
        if top_k_values is None:
            top_k_values = self.config['benchmark'].get('retrieval_top_k', [1, 5, 10])
        
        results = []
        print(f"\n{'='*60}")
        print(f"[Retrieve Benchmark V2] Testing {num_queries} queries")
        print(f"{'='*60}")
        
        queries = generate_query_vectors(vectors, num_queries)
        
        print("\n[1/2] Benchmarking Query Encryption...")
        t0 = time.perf_counter()
        _ = self.he_ctx.encrypt_batch(queries)
        enc_time = time.perf_counter() - t0
        results.append(TimingResult(
            component='encryption',
            operation='encrypt_query',
            total_time=enc_time,
            num_items=num_queries,
            avg_time_per_item=enc_time / num_queries,
            communication_bytes=0
        ))
        print(f"      Total: {enc_time:.4f}s")
        
        print("\n[2/2] Benchmarking Secure Search (Variant 2)...")
        for k in top_k_values:
            print(f"\n      Testing top_k={k}...")
            
            # Reset communication counter before search
            self.hnsw.reset_communication_counter()
            
            t_search_start = time.perf_counter()
            for q in queries:
                self.hnsw.search(q, k)
            search_total = time.perf_counter() - t_search_start
            
            # Get communication cost
            comm_bytes = self.hnsw.get_communication_bytes()
            
            results.append(TimingResult(
                component='secure_hnsw2',
                operation=f'search_top{k}',
                total_time=search_total,
                num_items=num_queries,
                avg_time_per_item=search_total / num_queries,
                communication_bytes=comm_bytes
            ))
            print(f"      Total: {search_total:.4f}s")
            print(f"      Communication: {comm_bytes / (1024*1024):.2f} MB")
            
        self.results.retrieve_results = results
        return results
    
    # ==================== Update Phase ====================
    
    def benchmark_update(self, vectors: np.ndarray, batch_sizes: List[int] = None) -> List[TimingResult]:
        """Test Update"""
        if batch_sizes is None:
            batch_sizes = self.config['benchmark'].get('update_batch_sizes', [1, 10, 100])
        
        dim = vectors.shape[1]
        results = []
        print(f"\n{'='*60}")
        print(f"[Update Benchmark V2] Testing batch sizes: {batch_sizes}")
        print(f"{'='*60}")
        
        for batch_size in batch_sizes:
            print(f"\n--- Batch size: {batch_size} ---")
            new_vectors = generate_update_vectors(dim, batch_size)
            
            t0 = time.perf_counter()
            self.hnsw.build_index(new_vectors)
            insert_time = time.perf_counter() - t0
            
            results.append(TimingResult(
                component='secure_hnsw2',
                operation=f'insert_batch{batch_size}',
                total_time=insert_time,
                num_items=batch_size,
                avg_time_per_item=insert_time / batch_size,
                communication_bytes=0
            ))
            print(f"      Total: {insert_time:.4f}s")
            
        self.results.update_results = results
        return results
    
    def run_all(self, output_path: str = "./results/timings2.json") -> BenchmarkResult:
        print("\n" + "="*70)
        print("PP-RAG Real CKKS Benchmark Suite - Variant 2")
        print("(Hybrid with Partial Client Decryption)")
        print("="*70)
        
        vectors = self.load_data()
        self.benchmark_setup(vectors)
        self.benchmark_retrieve(vectors)
        self.benchmark_update(vectors)
        
        self.results.save(output_path)
        print("\nBenchmark Complete!")
        return self.results


def run_benchmark(config_path: str = "./config/config.yaml"):
    runner = BenchmarkRunner2(config_path)
    return runner.run_all()
