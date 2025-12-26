#!/usr/bin/env python3
"""
07_run_multiscale.py
多级规模基准测试：分别对10万、100万、1000万条数据运行相同测试
"""
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.data_generator import (
    load_config, load_dataset, get_sample_dataset,
    generate_query_vectors, generate_update_vectors
)
from src.python.bench_runner import BenchmarkRunner, BenchmarkResult
from src.python.visualizer import generate_scale_comparison_figures


class MultiScaleRunner:
    """多规模基准测试运行器"""
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.results = {}
        
    def run_scale(self, scale_name: str) -> dict:
        """运行单个规模的完整测试"""
        print(f"\n{'#'*70}")
        print(f"# Testing Scale: {scale_name.upper()}")
        print(f"{'#'*70}")
        
        # 获取该规模的配置
        scale_config = None
        for s in self.config['dataset']['scales']:
            if s['name'] == scale_name:
                scale_config = s
                break
        
        if not scale_config:
            raise ValueError(f"Unknown scale: {scale_name}")
        
        data_path = scale_config['output_path']
        num_vectors = scale_config['num_vectors']
        
        # 检查数据文件是否存在
        if not Path(data_path).exists():
            print(f"[ERROR] Data file not found: {data_path}")
            print(f"  Run: python scripts/01_generate_data.py --scales {scale_name}")
            return None
        
        # 加载数据
        print(f"\nLoading {scale_name} dataset from {data_path}...")
        full_vectors = load_dataset(data_path)
        
        # 使用样本模式（对大规模数据尤其重要）
        use_sample = self.config['benchmark'].get('use_sample', True)
        if use_sample:
            sample_sizes = self.config['benchmark'].get('sample_sizes_per_scale', {})
            sample_size = sample_sizes.get(scale_name, 1000)
            print(f"Using sample mode: {sample_size:,} vectors (from {num_vectors:,})")
            vectors = get_sample_dataset(full_vectors, sample_size)
        else:
            vectors = full_vectors
        
        # 根据规模调整聚类数
        cluster_counts = self.config['index'].get('num_clusters_per_scale', {})
        num_clusters = cluster_counts.get(scale_name, self.config['index']['num_clusters'])
        
        # 创建运行器并设置自定义参数
        runner = BenchmarkRunner("./config/config.yaml")
        runner.config['index']['num_clusters'] = num_clusters
        
        # 运行三阶段测试
        scale_results = {
            'scale': scale_name,
            'num_vectors': num_vectors,
            'sample_size': len(vectors) if use_sample else num_vectors,
            'num_clusters': num_clusters,
            'setup': [],
            'retrieve': [],
            'update': []
        }
        
        # === SETUP阶段 ===
        print(f"\n{'='*60}")
        print(f"[{scale_name}] SETUP Phase")
        print(f"{'='*60}")
        
        setup_results = runner.benchmark_setup(vectors)
        scale_results['setup'] = [r.to_dict() for r in setup_results]
        
        total_setup = sum(r.total_time for r in setup_results)
        print(f"\nSetup total time: {total_setup:.4f}s")
        
        # === RETRIEVE阶段 ===
        print(f"\n{'='*60}")
        print(f"[{scale_name}] RETRIEVE Phase")
        print(f"{'='*60}")
        
        retrieve_results = runner.benchmark_retrieve(vectors)
        scale_results['retrieve'] = [r.to_dict() for r in retrieve_results]
        
        # === UPDATE阶段 ===
        print(f"\n{'='*60}")
        print(f"[{scale_name}] UPDATE Phase")
        print(f"{'='*60}")
        
        update_results = runner.benchmark_update(vectors)
        scale_results['update'] = [r.to_dict() for r in update_results]
        
        return scale_results
    
    def run_all_scales(self, scales: list = None) -> dict:
        """运行所有指定规模的测试"""
        if scales is None:
            scales = [s['name'] for s in self.config['dataset']['scales']]
        
        all_results = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'scales': {}
        }
        
        for scale_name in scales:
            result = self.run_scale(scale_name)
            if result:
                all_results['scales'][scale_name] = result
        
        return all_results
    
    def save_results(self, results: dict, output_path: str):
        """保存多规模测试结果"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n[Results] Saved to {output_path}")


def print_summary(results: dict):
    """打印多规模测试摘要"""
    print("\n" + "="*80)
    print("MULTI-SCALE BENCHMARK SUMMARY")
    print("="*80)
    
    # 表头
    print(f"\n{'Scale':<10} {'Vectors':>12} {'Sample':>10} {'Setup(s)':>12} {'Retrieve(ms)':>14} {'Update(s)':>12}")
    print("-"*80)
    
    for scale_name, scale_data in results['scales'].items():
        num_vectors = scale_data['num_vectors']
        sample_size = scale_data['sample_size']
        
        # 计算总时间
        setup_time = sum(r['total_time'] for r in scale_data['setup'])
        
        # 获取检索延迟（取search操作的平均值）
        retrieve_times = [r['avg_time_per_item'] * 1000 
                         for r in scale_data['retrieve'] 
                         if 'search' in r['operation']]
        avg_retrieve = sum(retrieve_times) / len(retrieve_times) if retrieve_times else 0
        
        # 计算更新总时间
        update_time = sum(r['total_time'] for r in scale_data['update'])
        
        print(f"{scale_name:<10} {num_vectors:>12,} {sample_size:>10,} {setup_time:>12.4f} {avg_retrieve:>14.4f} {update_time:>12.4f}")
    
    print("-"*80)
    print("\nNote: Retrieve latency is average per query in milliseconds")


def main():
    parser = argparse.ArgumentParser(description="Run multi-scale benchmark tests")
    parser.add_argument("--scales", nargs="+", choices=["100k", "1m", "10m", "all"],
                        default=["all"], help="Scales to test (default: all)")
    parser.add_argument("--output", type=str, default="./results/multiscale_timings.json",
                        help="Output file path")
    parser.add_argument("--visualize", action="store_true", 
                        help="Generate comparison visualizations")
    args = parser.parse_args()
    
    print("="*70)
    print("PP-RAG HE Benchmark - Multi-Scale Testing")
    print("="*70)
    
    # 确定要测试的规模
    config = load_config("./config/config.yaml")
    if "all" in args.scales:
        target_scales = [s['name'] for s in config['dataset']['scales']]
    else:
        target_scales = args.scales
    
    print(f"\nTarget scales: {', '.join(target_scales)}")
    
    # 运行测试
    runner = MultiScaleRunner("./config/config.yaml")
    results = runner.run_all_scales(target_scales)
    
    # 保存结果
    runner.save_results(results, args.output)
    
    # 打印摘要
    print_summary(results)
    
    # 可视化
    if args.visualize:
        print("\nGenerating scale comparison figures...")
        generate_scale_comparison_figures(args.output, "./results/figures")
    
    print("\n" + "="*70)
    print("Multi-scale benchmark complete!")
    print("="*70)


if __name__ == "__main__":
    main()
