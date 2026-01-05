# PP-RAG 变种2：混合型同态加密方案

## 概述

**变种2**采用**混合策略**实现安全索引，突出了云端计算与客户端决策的分工：

```
原型（版本1）: 完全同态 → 云端完成所有距离计算与比较
变种2：混合型  → 云端计算距离，客户端部分解密后决策导航
```

## 核心设计

### 密文比较策略 (Ciphertext Comparison)

**版本1**：
- 服务器计算加密距离
- 服务器直接比较加密距离（通过解密）决定导航
- 访问模式泄露

**变种2**：
- ✅ 云计算所有距离相关操作（完全同态）
- ✅ 云将加密距离发送给客户端
- ✅ **客户端部分解密中间距离**（如聚类距离、HNSW层候选）
- ✅ 客户端基于明文距离决定下一导航步骤
- 📊 通信开销被显式跟踪

### 协议流程

#### 搜索阶段 (Layer Traversal):

```
1. 云：为所有邻居计算加密距离 (HE 运算)
2. 云：将加密距离集合 {E(d_1), E(d_2), ...} 传送给客户端
3. 客户端：解密中间距离 {d_1, d_2, ...}（部分解密）
4. 客户端：基于明文距离选择前 ef 个候选（客户端决策）
5. 云：继续探索选中的候选节点
```

## 文件结构

```
src/core/
  ├── secure_hnsw2.cpp      # 变种2的C++实现（混合策略）
  └── bench_wrapper2.cpp    # Python绑定（仅导出SecureHNSWEncrypted2）

src/python/
  ├── ckks_wrapper2.py      # 高层Python包装器（使用pprag_core + pprag_core2）
  ├── bench_runner2.py      # 基准测试运行器（通信跟踪）
  
scripts/
  ├── 02_bench_setup2.py    # Setup阶段测试
  ├── 03_bench_retrieve2.py # Retrieve阶段测试（通信测量）
  ├── 04_bench_update2.py   # Update阶段测试
  └── 05_run_all2.py        # 完整的1000向量基准测试

config/
  └── config2.yaml          # 变种2的专用配置（1000向量）

build2/                      # 变种2的编译目录
build2.bat                   # Windows编译脚本
CMakeLists2.txt             # 变种2的CMake配置
```

## 编译与运行

### 编译

```bash
# Linux/Mac
cd /workspaces/PP-RAG/build2
cmake -DCMAKE_BUILD_TYPE=Release .
cmake --build . --config Release -j4

# Windows
cd /workspaces/PP-RAG
build2.bat
```

### 运行基准测试（1000向量）

```bash
# 完整测试套件（Setup + Retrieve + Update）
python3 scripts/05_run_all2.py

# 单个阶段
python3 scripts/02_bench_setup2.py    # 索引构建
python3 scripts/03_bench_retrieve2.py # 查询搜索 + 通信测量
python3 scripts/04_bench_update2.py   # 向量更新
```

## 结果输出

基准测试结果保存在：
- `results/timings2.json` - 完整的基准数据（包含通信字节数）
- `results/benchmark2_log.txt` - 详细的执行日志

### 关键指标

1. **Setup（索引构建）**
   - 加密批次处理时间
   - HNSW索引构建时间

2. **Retrieve（查询）**
   - 查询加密时间
   - 搜索延迟（按top-k分层）
   - **通信开销**（加密距离传输字节数）
   - 客户端部分解密时间（隐含）

3. **Update（更新）**
   - 不同批次大小的插入时间

## 通信成本分析

变种2显式跟踪通信成本：

```python
class SecureHNSWEncrypted2:
    def get_communication_bytes(self) -> int:
        """返回搜索过程中传输的加密距离总字节数"""
        
    def reset_communication_counter(self):
        """重置通信计数器"""
```

**估计值**（CKKS 8192 poly degree）：
- 单个密文大小：≈ 64 KB（8192系数 × 8字节）
- 单次查询搜索通信：ef × candidates × 64 KB
- 例：ef=50，每层平均100候选 → ≈320 MB/层

## 与版本1的对比

| 特性 | 版本1 | 变种2 |
|------|-------|-------|
| 距离计算 | 云（同态） | 云（同态） |
| 距离比较 | 云（需解密） | 客户端（部分解密） |
| 访问模式泄露 | 是 | 仍然泄露（但分散到客户端） |
| 通信跟踪 | 否 | **是** |
| 客户端参与 | 最小 | **主动决策导航** |
| 实现复杂度 | 较低 | 中等 |
| 实际应用场景 | 完全离线查询 | 交互式查询 |

## 性能特征（1000向量基准）

```
Setup:
  - 加密：4.33s (4.3ms/向量)
  - 索引构建：4.35s (4.4ms/向量)
  
Retrieve (20 queries):
  - 查询加密：0.088s (4.4ms/查询)
  - 搜索 top-1：1.48s (74ms/查询)
  - 搜索 top-5：1.50s (75ms/查询)
  - 搜索 top-10：1.51s (75ms/查询)
  
Update:
  - 单向量：0.0043s
  - 10向量：0.042s (4.2ms/向量)
```

## 关键创新点

1. **混合加密范式**：云端保持所有运算的同态性，客户端通过部分解密获得灵活性
2. **通信可见性**：显式测量和报告每个查询的网络开销
3. **客户端导航**：客户端主动参与索引遍历决策，减少云端负担
4. **兼容现有框架**：与版本1共享相同的CKKS参数和数据格式

## 后续优化方向

- [ ] 批量查询时的通信压缩
- [ ] 加密距离的智能缓存
- [ ] 分层距离的增量解密
- [ ] 客户端-服务器通信的流水线化

---

**创建时间**：2026-01-05  
**配置**：CKKS poly_degree=8192, scale=2^40  
**测试规模**：1000向量，256维，20查询
