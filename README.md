# PP-RAG Benchmark (Real SEAL CKKS)

> **Latest Commit**: 2025-12-28 13:53:12 UTC | Performance Optimizations: OpenMP Parallelization, HNSW Tuning, Compiler Optimizations

**Privacy-preserving RAG system — homomorphic-encryption component benchmark**. Implements PolySoftmin approximate comparisons over encrypted HNSW indexes using Microsoft SEAL.

## 📋 Features

- **CKKS encryption**: Homomorphic operations built on the C++ Microsoft SEAL library.
  - ✓ OpenMP-parallelized batch encryption
  - ✓ Compiler optimizations: LTO, -O3, -march=native, MSVC /arch:AVX2
- **PolySoftmin**: Polynomial approximation of the Softmin function in the homomorphic domain.
- **Secure HNSW**: Fully-encrypted graph index construction and search (vectors and distance computations remain in ciphertext).
  - ✓ Parameter tuning (M=8, ef_construction=100, ef_search=50)
- **Multi-scale benchmarking**: Supports benchmarks at 100k, 1M, and 10M vector scales.

## 🚀 Quick Start

Two startup options are provided. We recommend the scripted `bootstrap` flow, which builds the project locally without requiring sudo.

### Recommended (single-step bootstrap, builds SEAL locally without sudo)

The script builds Microsoft SEAL in-repo (under `thirdparty/seal_install`), builds `pprag_core`, and copies the produced Python extension into the repository root so you can run `python3 scripts/05_run_all.py` directly.

```bash
# After cloning the repo (run once)
git clone https://github.com/eulermachine/PP-RAG.git
cd PP-RAG

# One-shot bootstrap (this may take a while — downloads and builds SEAL)
scripts/bootstrap.sh

# Run the benchmark (bootstrap copies the extension to repo root, so no extra env vars are required)
python3 scripts/05_run_all.py

# Or, if you prefer to use the extension from the build directory:
PYTHONPATH=build python3 scripts/05_run_all.py
```

### Alternative (system-wide SEAL installation / manual)

If you prefer to install SEAL system-wide (requires admin privileges), build and install SEAL first, then build `pprag_core`:

```bash
# From SEAL source dir (or via package manager)
cmake -S . -B build && sudo cmake --build build --target install

# Then build pprag_core in this project:
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

You can then use `PYTHONPATH=build` or install the produced `.so/.pyd` into your Python environment so `import pprag_core` works globally.

### Dependencies & recommendations

- `Python 3.8+`, `CMake 3.14+`, and a C++ compiler (GCC/Clang or MSVC).
- We recommend running `scripts/bootstrap.sh` to avoid manual SEAL configuration or using sudo.
- Performance tips: the project uses OpenMP, LTO, and tuned HNSW defaults — use a Release build for best performance.

### Generate & run example

Generate the 100k dataset and run the benchmark (bootstrap will auto-generate missing data):

```bash
PYTHONPATH=build python3 scripts/01_generate_data.py --scales 100k
PYTHONPATH=build python3 scripts/05_run_all.py
```

## 📊 Results

Benchmark outputs are stored in the `results/` directory:
- `timings.json`: raw performance measurements
- `figures/*.png`: auto-generated visualizations (setup time, retrieval latency, etc.)

> ⚠️ Performance note:
> Homomorphic encryption is computationally expensive.
> - Encrypting 100k vectors can take minutes.
> - Individual HNSW searches can be on the order of seconds (parameter-dependent).
> - We recommend validating with small sample sizes (`sample_size`) before scaling up.

## 🔧 Optimization highlights

This release includes the following performance improvements:

### 1. OpenMP-parallelized batch encryption
- The C++ `seal_utils.cpp` `encrypt_batch()` uses `#pragma omp parallel for`.
- The Python `ckks_wrapper.py` `encrypt_batch()` calls into C++ using a `ThreadPoolExecutor` to parallelize at the Python layer.

### 2. HNSW parameter tuning
- Faster defaults are applied in `config.yaml`.
- M=8 (was 16), ef_construction=100 (was 200), ef_search=50 (was 100).
- Reduced memory and construction time.

### 3. Compiler optimizations
- **GCC/Clang**: `-O3 -march=native -flto`
- **MSVC**: `/arch:AVX2 /GL /LTCG`
- Link-time optimization (LTO) is enabled to improve runtime performance.

### 4. Flexible benchmark scales
- `config.yaml` allows tuning per-scale vector counts and sample sizes.
- Supports `benchmark.use_sample` and `sample_sizes_per_scale` for quick validation.

## 📝 Script overview

- `01_generate_data.py`: generate synthetic datasets at multiple scales
- `02_bench_setup.py`: run the Setup phase only (encryption + HNSW build)
- `03_bench_retrieve.py`: run the Retrieve phase only (query encryption + secure search)
- `04_bench_update.py`: run the Update phase only (incremental index updates)
- `05_run_all.py`: run the full benchmark and generate visualizations
- `07_run_multiscale.py`: multi-scale comparison runs

## 📄 License

See [LICENSE](./LICENSE).
