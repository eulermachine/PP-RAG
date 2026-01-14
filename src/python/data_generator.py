"""
Efficient vector data generation utilities.
Optimizations: use NumPy vectorized operations to avoid Python loops.
"""
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import yaml


def load_config(config_path: str = "./config/config.yaml") -> dict:
    """Load configuration file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_synthetic_embeddings(
    num: int, 
    dim: int, 
    normalize: bool = True,
    dtype: np.dtype = np.float32
) -> np.ndarray:
    """
    Efficiently generate synthetic (optionally normalized) embedding vectors.

    Args:
        num: number of vectors
        dim: vector dimension
        normalize: whether to normalize each vector
        dtype: data type

    Returns:
        An array of shape (num, dim)
    """
    # Use NumPy vectorized generation — much faster than Python loops
    data = np.random.randn(num, dim).astype(dtype)
    
    if normalize:
        # Vectorized normalization
        norms = np.linalg.norm(data, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.maximum(norms, 1e-10)
        data = data / norms
    
    return data


def generate_query_vectors(
    dataset: np.ndarray,
    num_queries: int,
    noise_level: float = 0.1
) -> np.ndarray:
    """
    Generate test query vectors by sampling the dataset and adding noise.

    Args:
        dataset: base dataset
        num_queries: number of queries to generate
        noise_level: noise amplitude

    Returns:
        Array of query vectors
    """
    # Random sampling
    indices = np.random.choice(len(dataset), num_queries, replace=False)
    queries = dataset[indices].copy()
    
    # Add noise to make queries more realistic
    noise = np.random.randn(*queries.shape).astype(queries.dtype) * noise_level
    queries = queries + noise
    
    # Re-normalize
    norms = np.linalg.norm(queries, axis=1, keepdims=True)
    queries = queries / np.maximum(norms, 1e-10)
    
    return queries


def generate_update_vectors(
    dim: int,
    batch_size: int,
    dtype: np.dtype = np.float32
) -> np.ndarray:
    """Generate new vectors for update/insert benchmarks."""
    return generate_synthetic_embeddings(batch_size, dim, normalize=True, dtype=dtype)


def save_dataset(data: np.ndarray, path: str) -> None:
    """Save dataset to a .npy file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.save(path, data)
    print(f"[DataGenerator] Saved {data.shape} to {path}")


def load_dataset(path: str) -> np.ndarray:
    """Load a dataset from a .npy file."""
    data = np.load(path)
    print(f"[DataGenerator] Loaded {data.shape} from {path}")
    return data


def get_sample_dataset(
    full_dataset: np.ndarray, 
    sample_size: int
) -> np.ndarray:
    """Return a random subset of the dataset for quick validation."""
    if sample_size >= len(full_dataset):
        return full_dataset
    indices = np.random.choice(len(full_dataset), sample_size, replace=False)
    return full_dataset[indices]
