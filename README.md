# PP-RAG Benchmark (Real SEAL CKKS)

**隐私保护 RAG 系统同态加密组件基准测试** - 基于 Microsoft SEAL 实现在密文 HNSW 索引上的 PolySoftmin 近似比较。

## 📋 功能特性

- **真实 CKKS 加密**: 使用 C++ Microsoft SEAL 库进行全同态计算。
- **PolySoftmin**: 在同态加密域下使用多项式近似实现 Softmin 函数。
- **Secure HNSW**: 图索引的全密文构建与搜索（向量与距离计算均在密文域）。
- **多级规模测试**: 支持 10万、100万、1000万 级别向量数据的基准测试。

## 🚀 快速开始

### 1. 环境准备

- **Python**: 3.8+
- **C++**: Visual Studio 2019+ (Windows) 或 GCC/Clang (Linux)
- **CMake**: 3.14+
- **SEAL**: [Microsoft SEAL 4.1+](https://github.com/microsoft/SEAL) (必须预先安装)

### 2. 编译 C++ 核心模块

本项目依赖 C++ 编写的 `pprag_core` 模块。

**Windows:**
直接运行构建脚本：
```powershell
.\build.bat
```

**Linux/Manual:**
```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
cp pprag_core*.so ..  # 或 pyd
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 4. 运行基准测试

**生成数据:**
```bash
# 生成 100k 数据集 (约 600MB)
python scripts/01_generate_data.py --scales 100k
```

**运行测试:**
```bash
# 运行 100k 规模测试
python scripts/07_run_multiscale.py --scales 100k --visualize
```

## 📊 测试结果

测试结果将保存在 `results/` 目录：
- `multiscale_timings.json`: 原始性能数据
- `figures/*.png`: 自动生成的可视化图表（包括Setup时间、检索延迟等）

> ⚠️ **性能提示**: 
> 真实同态加密运算非常耗时。
> - 加密 100k 向量可能需要数分钟。
> - 单次 HNSW 搜索可能需要秒级时间（取决于参数）。
> - 建议先使用 `scripts/07_run_multiscale.py` 中的 `sample_size` 参数进行小规模验证。
