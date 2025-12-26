#!/usr/bin/env python3
"""
03_bench_retrieve.py
测试Retrieve阶段：查询加密、安全HNSW搜索
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.bench_runner import BenchmarkRunner


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Retrieve Phase")
    print("="*60)
    
    runner = BenchmarkRunner("./config/config.yaml")
    vectors = runner.load_data()
    
    # 需要先构建索引
    print("\n[Prerequisite] Building index first...")
    runner.benchmark_setup(vectors)
    
    # 运行检索测试
    results = runner.benchmark_retrieve(vectors)
    
    # 打印摘要
    print("\n" + "="*60)
    print("Retrieve Phase Summary")
    print("="*60)
    
    for r in results:
        if 'search' in r.operation:
            print(f"\n{r.operation}:")
            print(f"  Total: {r.total_time:.4f}s")
            print(f"  Avg per query: {r.avg_time_per_item*1000:.4f}ms")
    
    runner.results.save("./results/retrieve_timings.json")


if __name__ == "__main__":
    main()
