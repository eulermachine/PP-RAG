# PP-RAG Benchmark (Real SEAL CKKS)

**隐私保护 RAG 系统同态加密组件基准测试** - 基于 Microsoft SEAL 实现在密文 HNSW 索引上的 PolySoftmin 近似比较。

## 📋 功能特性

- **真实 CKKS 加密**: 使用 C++ Microsoft SEAL 库进行全同态计算。
- **PolySoftmin**: 在同态加密域下使用多项式近似实现 Softmin 函数。
- **Secure HNSW**: 图索引的全密文构建与搜索（向量与距离计算均在密文域）。
- **多级规模测试**: 支持 10万、100万、1000万 级别向量数据的基准测试。

## 🚀 快速开始

以下为两种可选的启动方式：推荐使用脚本化的 `bootstrap` 流程，用户无需 sudo 即可在本地构建并直接运行项目。

### 推荐（单步引导，本地构建 SEAL，无需 sudo）

脚本会在仓库内构建 Microsoft SEAL（到 `thirdparty/seal_install`），编译 `pprag_core`，并将生成的扩展复制到仓库根，方便直接 `python3 scripts/05_run_all.py` 运行。

```bash
# 克隆仓库后（只需执行一次）
git clone https://github.com/eulermachine/PP-RAG.git
cd PP-RAG

# 一键引导（会花一些时间，下载并构建 SEAL）
scripts/bootstrap.sh

# 运行基准（bootstrap 会把扩展复制到仓库根，因此无需额外环境变量）
python3 scripts/05_run_all.py

# 或者若你希望使用构建目录下的扩展：
PYTHONPATH=build python3 scripts/05_run_all.py
```

### 备选（手动 / 系统范围安装 SEAL）

如果你希望把 SEAL 安装到系统路径并对所有用户可用，可以先安装 SEAL（需要管理员权限）：

```bash
# 在 SEAL 源码目录执行（或使用系统包管理器）
cmake -S . -B build && sudo cmake --build build --target install

# 然后在项目中构建 pprag_core：
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

随后你可以使用 `PYTHONPATH=build` 或把生成的 `.so/.pyd` 安装到系统 Python，使 `import pprag_core` 在任意位置可用。

### 依赖与建议

- `Python 3.8+`, `CMake 3.14+`, C++ 编译器（GCC/Clang 或 MSVC）。
- 推荐先运行 `scripts/bootstrap.sh` 来避免手动配置 SEAL 路径或使用 sudo。

### 生成与运行示例

生成 100k 数据集并运行（bootstrap 会自动生成数据，如缺失）：

```bash
PYTHONPATH=build python3 scripts/01_generate_data.py --scales 100k
PYTHONPATH=build python3 scripts/05_run_all.py
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
