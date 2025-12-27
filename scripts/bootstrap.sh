#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script to allow users to clone and run the project without sudo.
# - Builds Microsoft SEAL locally into thirdparty/seal_install
# - Configures and builds the project with that SEAL
# - Copies the built pprag_core Python extension to the repo root for easy import
# - Optionally generates the 100k dataset and runs the benchmark

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1) Build SEAL locally (no sudo)
SEAL_DIR="$ROOT_DIR/thirdparty/seal_install"
if [ ! -d "$ROOT_DIR/SEAL" ]; then
  echo "SEAL source not found in repository; cloning into SEAL/"
  git clone --depth 1 https://github.com/microsoft/SEAL.git SEAL
fi

pushd SEAL
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$SEAL_DIR" ..
cmake --build . --target install -j"$(nproc)"
popd

# 2) Configure and build this project using local SEAL
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DSEAL_DIR="$SEAL_DIR/lib/cmake/SEAL-4.1"
cmake --build build -j"$(nproc)"

# 3) Copy pprag_core extension to repo root so "import pprag_core" works without PYTHONPATH
SO_SRC="$(ls build/pprag_core*.so 2>/dev/null || true)"
if [ -n "$SO_SRC" ]; then
  echo "Copying $SO_SRC -> $ROOT_DIR/pprag_core.so"
  cp -f "$SO_SRC" "$ROOT_DIR/pprag_core.so"
else
  echo "Built pprag_core extension not found in build/"
fi

# 4) Generate small dataset if missing
if [ ! -f "$ROOT_DIR/data/vectors_100k_768d.npy" ]; then
  echo "Generating 100k test dataset..."
  PYTHONPATH=build python3 scripts/01_generate_data.py --scales 100k
fi

# 5) Run a quick 1k-sample test; on success run larger scales automatically
echo "\nRunning quick 1k-sample verification test..."
# Disable exit-on-error for the quick test so we can capture the result
set +e
PYTHONPATH=build python3 - <<'PY'
from pathlib import Path
from src.python.data_generator import load_config
from src.python.bench_runner import run_benchmark
cfg = load_config('./config/config.yaml')
# prepare a temporary config for quick sample run (100k dataset, sample mode)
tmp = cfg.copy()
tmp['dataset'] = dict(tmp.get('dataset', {}))
scales = cfg.get('dataset', {}).get('scales', [])
out100k = None
for s in scales:
    if s.get('name') == '100k':
        out100k = s.get('output_path')
        break
if out100k is None:
    raise SystemExit('100k scale not found in config')
tmp['dataset']['output_path'] = out100k
tmp['benchmark'] = dict(tmp.get('benchmark', {}))
tmp['benchmark']['use_sample'] = True
tmp['dataset']['sample_size'] = tmp['dataset'].get('sample_size', 1000)
import yaml, tempfile
tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
tmpf.write(yaml.safe_dump(tmp).encode('utf-8'))
tmpf.flush()
tmpf.close()
print(f"Running quick benchmark with config: {tmpf.name}")
run_benchmark(tmpf.name)
print('\nQuick run finished')
PY
rc=$?
set -e
if [ $rc -ne 0 ]; then
  echo "Quick 1k-sample test failed (exit $rc). Aborting larger-scale runs."
else
  echo "Quick test passed. Starting full-scale runs for 100k, 1m, 10m..."
  for SCALE in 100k 1m 10m; do
    echo "\nPreparing full run for scale: $SCALE"
    PYTHONPATH=build python3 - <<'PY'
from pathlib import Path
from src.python.data_generator import load_config, generate_synthetic_embeddings, save_dataset
from src.python.bench_runner import run_benchmark
import yaml, tempfile
cfg = load_config('./config/config.yaml')
scales = cfg.get('dataset', {}).get('scales', [])
sel = None
for s in scales:
    if s.get('name') == '$SCALE':
        sel = s
        break
if sel is None:
    raise SystemExit(f'Scale $SCALE not defined in config')
out = sel['output_path']
num = sel['num_vectors']
dim = cfg.get('dataset', {}).get('dimension', 768)
# generate dataset if missing
if not Path(out).exists():
    print(f"Dataset {out} missing; generating {num} vectors (this may take time)...")
    data = generate_synthetic_embeddings(num, dim)
    save_dataset(data, out)
else:
    print(f"Dataset {out} already exists; skipping generation")
tmp = cfg.copy()
tmp['dataset'] = dict(tmp.get('dataset', {}))
tmp['dataset']['output_path'] = out
tmp['benchmark'] = dict(tmp.get('benchmark', {}))
tmp['benchmark']['use_sample'] = False
tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
tmpf.write(yaml.safe_dump(tmp).encode('utf-8'))
tmpf.flush()
tmpf.close()
print(f"Running full benchmark for $SCALE with config {tmpf.name}")
run_benchmark(tmpf.name)
print(f"Finished full run for $SCALE")
PY
  done
  echo "\nAll requested full-scale runs complete."
fi

# 5) Run benchmark (optional). Uncomment to run automatically.
# echo "Running benchmark..."
# PYTHONPATH=build python3 scripts/05_run_all.py

cat <<EOF
Bootstrap complete.
To run the benchmark now:
  PYTHONPATH=build python3 scripts/05_run_all.py
Or run without PYTHONPATH because bootstrap copied the extension:
  python3 scripts/05_run_all.py
EOF
