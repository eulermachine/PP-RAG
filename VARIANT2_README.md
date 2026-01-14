# PP-RAG 变种2：混合型同态加密方案

## 概述

**变种2**采用**混合策略**实现安全索引，突出了云端计算与客户端决策的分工：

```
原型（版本1）: 完全同态 → 云端完成所有距离计算与比较
变种2：混合型  → 云端计算距离，客户端部分解密后决策导航
```

## 核心设计

### 密文比较策略 (Ciphertext Comparison)

````markdown
# PP-RAG Variant 2 — Hybrid Homomorphic Scheme

## Overview

Variant 2 uses a hybrid approach for secure indexing that clearly separates cloud computation from client decision-making:

```
Prototype (Version 1): Fully homomorphic — the cloud performs all distance computations and comparisons
Variant 2 (Hybrid): Cloud computes distances; the client partially decrypts intermediate distances and makes navigation decisions
```

## Core Design

### Ciphertext Comparison Strategy

Version 1:
- The server computes encrypted distances
- The server compares encrypted distances (via decryption) to decide navigation
- Access patterns are leaked

Variant 2:
- ✅ The cloud performs all distance-related operations (fully homomorphic)
- ✅ The cloud sends encrypted distances to the client
- ✅ The client partially decrypts intermediate distances (e.g., cluster distances, HNSW layer candidates)
- ✅ The client uses plaintext distances to decide the next navigation steps
- 📊 Communication overhead is explicitly tracked

### Protocol Flow

#### Search Phase (Layer Traversal):

```
1. Cloud: compute encrypted distances for all neighbors (HE operations)
2. Cloud: send the set of encrypted distances {E(d_1), E(d_2), ...} to the client
3. Client: partially decrypt the intermediate distances {d_1, d_2, ...}
4. Client: select the top-ef candidates in plaintext (client decision)
5. Cloud: continue exploring the selected candidate nodes
```

## File Layout

```
src/core/
  ├── secure_hnsw2.cpp      # C++ implementation for Variant 2 (hybrid strategy)
  └── bench_wrapper2.cpp    # Python bindings (exports SecureHNSWEncrypted2)

src/python/
  ├── ckks_wrapper2.py      # High-level Python wrapper (uses pprag_core + pprag_core2)
  └── bench_runner2.py      # Benchmark runner with communication tracking

scripts/
  ├── 02_bench_setup2.py    # Setup phase benchmark
  ├── 03_bench_retrieve2.py # Retrieve phase benchmark (measures communication)
  ├── 04_bench_update2.py   # Update phase benchmark
  └── 05_run_all2.py        # Full 1k-vector benchmark workflow

config/
  └── config2.yaml          # Variant 2 specific config (1k vectors)

build2/                      # Build directory for Variant 2
build2.bat                   # Windows build script
CMakeLists2.txt              # CMake configuration for Variant 2
```

## Build & Run

### Build

```bash
# Linux/macOS
cd /workspaces/PP-RAG/build2
cmake -DCMAKE_BUILD_TYPE=Release .
cmake --build . --config Release -j4

# Windows
cd /workspaces/PP-RAG
build2.bat
```

### Run the 1k-vector benchmark

```bash
# Full test suite (Setup + Retrieve + Update)
python3 scripts/05_run_all2.py

# Per-phase runs
python3 scripts/02_bench_setup2.py    # index build
python3 scripts/03_bench_retrieve2.py # query search + communication measurement
python3 scripts/04_bench_update2.py   # vector updates
```

## Results

Benchmark outputs are stored at:
- `results/timings2.json` — full benchmark data (includes communication bytes)
- `results/benchmark2_log.txt` — detailed execution log

### Key Metrics

1. Setup (index build)
   - encryption batch processing time
   - HNSW index build time

2. Retrieve (queries)
   - query encryption time
   - search latency (per top-k)
   - **communication cost** (bytes transferred for encrypted distances)
   - client partial decryption time (implicit)

3. Update
   - insertion time for different batch sizes

## Communication Cost Analysis

Variant 2 explicitly tracks communication cost:

```python
class SecureHNSWEncrypted2:
    def get_communication_bytes(self) -> int:
        """Return total bytes of encrypted-distance data transferred during a search."""

    def reset_communication_counter(self):
        """Reset the communication counter."""
```

Estimated values (CKKS, poly_degree=8192):
- Ciphertext size ≈ 64 KB (8192 coefficients × 8 bytes)
- Per-query transfer ≈ ef × candidates × 64 KB
- Example: ef=50, ~100 candidates/layer → ~320 MB per layer

## Comparison with Version 1

| Feature               | Version 1         | Variant 2 (Hybrid)       |
|-----------------------|-------------------|--------------------------|
| Distance computation  | Cloud (HE)        | Cloud (HE)               |
| Distance comparison   | Cloud (decrypt)   | Client (partial decrypt) |
| Access pattern leak   | Yes               | Still leaked (client-side)
| Communication tracking| No                | **Yes**                  |
| Client involvement    | Minimal           | **Active decision-making**|
| Implementation effort | Lower             | Medium                   |
| Use case             | Offline queries    | Interactive queries      |

## Performance (1k-vector benchmark)

```
Setup:
  - encryption: 4.33s (4.3 ms/vector)
  - index build: 4.35s (4.4 ms/vector)

Retrieve (20 queries):
  - query encryption: 0.088s (4.4 ms/query)
  - search top-1: 1.48s (74 ms/query)
  - search top-5: 1.50s (75 ms/query)
  - search top-10: 1.51s (75 ms/query)

Update:
  - single vector: 0.0043s
  - 10 vectors: 0.042s (4.2 ms/vector)
```

## Key Innovations

1. Hybrid encryption paradigm: the cloud preserves homomorphic computation while the client gains flexibility via partial decryption.
2. Communication visibility: explicit measurement and reporting of per-query network overhead.
3. Client-driven navigation: the client actively participates in index traversal decisions, reducing cloud load.
4. Compatibility: shares CKKS parameters and data formats with Version 1.

## Future Work

- [ ] Communication compression for batch queries
- [ ] Smart caching for encrypted distances
- [ ] Incremental decryption for layered distances
- [ ] Pipeline client-server communication

---

**Created**: 2026-01-05  
**Config**: CKKS poly_degree=8192, scale=2^40  
**Test scale**: 1000 vectors, 256 dims, 20 queries

````
