#!/usr/bin/env python3
"""
01_generate_data.py
生成多级规模向量数据集：十万、百万、千万条768维模拟向量数据
"""
import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.data_generator import (
    load_config, generate_synthetic_embeddings, save_dataset
)


def generate_single_scale(num_vectors: int, dimension: int, output_path: str, scale_name: str):
    """生成单个规模的数据集"""
    print(f"\n{'='*60}")
    print(f"Generating {scale_name} dataset: {num_vectors:,} vectors")
    print(f"{'='*60}")
    
    # 检查是否已存在
    if Path(output_path).exists():
        print(f"[SKIP] Dataset already exists at {output_path}")
        print("  Use --force to regenerate")
        return False
    
    print(f"Dimension: {dimension}")
    print(f"Output: {output_path}")
    
    # 生成数据
    vectors = generate_synthetic_embeddings(num_vectors, dimension)
    
    print(f"Generated shape: {vectors.shape}")
    print(f"Memory size: {vectors.nbytes / 1024 / 1024:.2f} MB")
    
    # 保存
    save_dataset(vectors, output_path)
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate multi-scale vector datasets")
    parser.add_argument("--scales", nargs="+", choices=["100k", "1m", "10m", "all"],
                        default=["all"], help="Scales to generate (default: all)")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing files")
    args = parser.parse_args()
    
    print("="*70)
    print("PP-RAG HE Benchmark - Multi-Scale Dataset Generation")
    print("="*70)
    
    # 加载配置
    config = load_config("./config/config.yaml")
    dimension = config['dataset']['dimension']
    scales = config['dataset']['scales']
    
    # 确定要生成的规模
    if "all" in args.scales:
        target_scales = [s['name'] for s in scales]
    else:
        target_scales = args.scales
    
    generated = []
    skipped = []
    
    for scale_config in scales:
        scale_name = scale_config['name']
        if scale_name not in target_scales:
            continue
            
        num_vectors = scale_config['num_vectors']
        output_path = scale_config['output_path']
        
        # 如果指定了force，删除已存在的文件
        if args.force and Path(output_path).exists():
            Path(output_path).unlink()
            print(f"[FORCE] Removed existing {output_path}")
        
        success = generate_single_scale(num_vectors, dimension, output_path, scale_name)
        
        if success:
            generated.append(scale_name)
        else:
            skipped.append(scale_name)
    
    # 打印摘要
    print("\n" + "="*70)
    print("Dataset Generation Summary")
    print("="*70)
    
    if generated:
        print(f"\n✓ Generated: {', '.join(generated)}")
    if skipped:
        print(f"○ Skipped (already exist): {', '.join(skipped)}")
    
    print("\nData files:")
    for scale_config in scales:
        path = Path(scale_config['output_path'])
        status = "✓" if path.exists() else "✗"
        size = f"{path.stat().st_size / 1024 / 1024:.0f} MB" if path.exists() else "N/A"
        print(f"  {status} {scale_config['name']:>4}: {path} ({size})")


if __name__ == "__main__":
    main()
