#!/usr/bin/env python3
"""
bench_encrypt_batch.py
性能采样脚本：测试 encrypt_batch 的并行性能（Python 层 ThreadPoolExecutor）
"""
import sys
from pathlib import Path
import numpy as np
from pyinstrument import Profiler

sys.path.insert(0, str(Path(__file__).parent))

from src.python.ckks_wrapper import HEContext
from src.python.data_generator import load_config, load_dataset, get_sample_dataset

def main():
    # 加载配置和数据
    config = load_config("./config/config.yaml")
    full_vectors = load_dataset("./data/vectors_100k_256d.npy")
    
    # 使用小样本（1000）进行采样
    vectors = get_sample_dataset(full_vectors, 1000)
    print(f"Testing encrypt_batch with {len(vectors)} vectors")
    
    # 初始化 HE 上下文
    he_ctx = HEContext(config)
    
    # 开始性能采样
    profiler = Profiler()
    profiler.start()
    
    # 运行 encrypt_batch（应该使用 ThreadPoolExecutor 并行化）
    print("Running encrypt_batch (parallel with ThreadPoolExecutor)...")
    encrypted = he_ctx.encrypt_batch(vectors)
    
    profiler.stop()
    
    # 输出报告
    print("\n" + "="*70)
    print("PROFILING REPORT: encrypt_batch (Python ThreadPoolExecutor)")
    print("="*70 + "\n")
    print(profiler.output_text(unicode=True, color=True, show_all=True))
    
    print(f"\nTotal encrypted vectors: {len(encrypted)}")
    print(f"Success: No errors, all vectors encrypted")

if __name__ == "__main__":
    main()
