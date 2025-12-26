"""
高效向量数据生成模块
优化: 使用numpy向量化操作，避免循环
"""
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import yaml


def load_config(config_path: str = "./config/config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_synthetic_embeddings(
    num: int, 
    dim: int, 
    normalize: bool = True,
    dtype: np.dtype = np.float32
) -> np.ndarray:
    """
    高效生成归一化的模拟嵌入向量
    
    Args:
        num: 向量数量
        dim: 向量维度
        normalize: 是否归一化
        dtype: 数据类型
    
    Returns:
        形状为 (num, dim) 的向量数组
    """
    # 使用numpy向量化生成，比循环快100x+
    data = np.random.randn(num, dim).astype(dtype)
    
    if normalize:
        # 向量化归一化
        norms = np.linalg.norm(data, axis=1, keepdims=True)
        # 避免除零
        norms = np.maximum(norms, 1e-10)
        data = data / norms
    
    return data


def generate_query_vectors(
    dataset: np.ndarray,
    num_queries: int,
    noise_level: float = 0.1
) -> np.ndarray:
    """
    生成测试查询向量（基于数据集采样+噪声）
    
    Args:
        dataset: 原始数据集
        num_queries: 查询数量
        noise_level: 噪声水平
    
    Returns:
        查询向量数组
    """
    # 随机采样
    indices = np.random.choice(len(dataset), num_queries, replace=False)
    queries = dataset[indices].copy()
    
    # 添加噪声使查询更真实
    noise = np.random.randn(*queries.shape).astype(queries.dtype) * noise_level
    queries = queries + noise
    
    # 重新归一化
    norms = np.linalg.norm(queries, axis=1, keepdims=True)
    queries = queries / np.maximum(norms, 1e-10)
    
    return queries


def generate_update_vectors(
    dim: int,
    batch_size: int,
    dtype: np.dtype = np.float32
) -> np.ndarray:
    """生成用于更新测试的新向量"""
    return generate_synthetic_embeddings(batch_size, dim, normalize=True, dtype=dtype)


def save_dataset(data: np.ndarray, path: str) -> None:
    """保存数据集到文件"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.save(path, data)
    print(f"[DataGenerator] Saved {data.shape} to {path}")


def load_dataset(path: str) -> np.ndarray:
    """加载数据集"""
    data = np.load(path)
    print(f"[DataGenerator] Loaded {data.shape} from {path}")
    return data


def get_sample_dataset(
    full_dataset: np.ndarray, 
    sample_size: int
) -> np.ndarray:
    """获取样本子集用于快速验证"""
    if sample_size >= len(full_dataset):
        return full_dataset
    indices = np.random.choice(len(full_dataset), sample_size, replace=False)
    return full_dataset[indices]
