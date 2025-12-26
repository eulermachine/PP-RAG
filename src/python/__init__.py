"""
PP-RAG HE Component Benchmark - Python Package
"""
from .data_generator import (
    generate_synthetic_embeddings,
    generate_query_vectors,
    generate_update_vectors,
    load_config,
    load_dataset,
    save_dataset,
    get_sample_dataset
)
from .ckks_wrapper import (
    HEContext,
    SecureHNSWWrapper
)
from .bench_runner import BenchmarkRunner, run_benchmark
from .visualizer import generate_all_figures

__all__ = [
    # Data generation
    'generate_synthetic_embeddings',
    'generate_query_vectors', 
    'generate_update_vectors',
    'load_config',
    'load_dataset',
    'save_dataset',
    'get_sample_dataset',
    # CKKS Wrapper
    'HEContext',
    'SecureHNSWWrapper',
    # Benchmark
    'BenchmarkRunner',
    'run_benchmark',
    # Visualization
    'generate_all_figures',
]
