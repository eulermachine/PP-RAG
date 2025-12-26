# PP-RAG HE Component Benchmark

**隐私保护RAG系统的同态加密组件性能基准测试框架**

## 📋 概述

本项目专注于测试PP-RAG系统核心加密组件的性能：

| 组件 | 描述 | 测试阶段 |
|------|------|----------|
| **PolySoftmin** | 多项式近似softmin函数 | Setup/Retrieve |
| **HomoNorm** | Goldschmidt迭代归一化 | Setup |
| **Secure K-Means** | 基于软分配的安全聚类 | Setup |
| **Secure HNSW** | 加密图索引构建与搜索 | Setup/Retrieve/Update |

## 🚀 快速开始

### 1. 安装依赖

```powershell
cd C:\Users\li\.gemini\antigravity\scratch\pp-rag-he-benchmark
pip install -r requirements.txt
```

### 2. 生成测试数据

```powershell
python scripts/01_generate_data.py
```

### 3. 运行完整测试

```powershell
# 运行完整基准测试并生成可视化
python scripts/05_run_all.py
```

或分阶段运行：

```powershell
python scripts/02_bench_setup.py     # Setup阶段
python scripts/03_bench_retrieve.py  # Retrieve阶段
python scripts/04_bench_update.py    # Update阶段
python scripts/06_visualize.py       # 生成图表
```

## 📁 项目结构

```
pp-rag-he-benchmark/
├── config/
│   ├── config.yaml          # 实验参数配置
│   └── ckks_128bit.json     # CKKS加密参数
├── data/                     # 生成的向量数据
├── src/
│   ├── core/                # C++核心实现
│   │   ├── poly_softmin.cpp
│   │   ├── homo_norm.cpp
│   │   ├── secure_kmeans.cpp
│   │   ├── secure_hnsw.cpp
│   │   └── bench_wrapper.cpp
│   └── python/              # Python测试框架
│       ├── data_generator.py
│       ├── he_simulator.py  # HE模拟器
│       ├── bench_runner.py
│       └── visualizer.py
├── scripts/                  # 测试脚本
│   ├── 01_generate_data.py
│   ├── 02_bench_setup.py
│   ├── 03_bench_retrieve.py
│   ├── 04_bench_update.py
│   ├── 05_run_all.py
│   └── 06_visualize.py
└── results/                  # 输出结果
    ├── timings.json
    └── figures/
```

## ⚙️ 配置说明

编辑 `config/config.yaml` 调整测试参数：

```yaml
dataset:
  num_vectors: 100000    # 向量数量
  sample_size: 1000      # 快速验证样本量

benchmark:
  use_sample: true       # true=使用样本, false=使用全量
  num_test_queries: 50   # 查询测试数量
  retrieval_top_k: [1, 5, 10]  # 测试的K值
```

## 📊 输出结果

运行测试后，`results/` 目录包含：

- `timings.json` - 详细耗时数据
- `figures/setup_breakdown.png` - Setup阶段分解图
- `figures/retrieval_latency_vs_topk.png` - 检索延迟曲线
- `figures/update_throughput.png` - 更新吞吐量
- `figures/component_details.png` - 组件内部耗时

## 🔧 可选：编译C++模块

如需使用真实SEAL库而非Python模拟：

```powershell
# 安装SEAL (参考 https://github.com/microsoft/SEAL)
# 然后编译
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

## 📝 注意事项

1. **样本模式**: 首次运行建议使用样本模式(`use_sample: true`)快速验证
2. **全量测试**: 10万向量的安全K-Means可能需要较长时间
3. **内存**: 全量测试需要约600MB内存 (100k × 768 × 4 bytes)
