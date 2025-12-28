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
  #!/usr/bin/env bash
  set -euo pipefail

  # Bootstrap script to allow users to clone and run the project without sudo.
  # - Builds Microsoft SEAL locally into thirdparty/seal_install (unless found)
  # - Configures and builds the project with that SEAL (unless built)
  # - Copies the built pprag_core Python extension to the repo root for easy import
  # - Optionally generates the 100k dataset and runs a quick verification

  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$ROOT_DIR"

  FORCE=false
  SKIP_SEAL=false
  SKIP_BUILD=false
  SKIP_DATA=false
  SKIP_QUICK=false

  usage() {
    cat <<EOF
  Usage: $0 [--force] [--skip-seal] [--skip-build] [--skip-data] [--skip-quick]

    --force       Rebuild SEAL and project even if artifacts exist
    --skip-seal   Do not build SEAL (use system SEAL or SEAL_DIR)
    --skip-build  Skip building the project
    --skip-data   Do not generate dataset
    --skip-quick  Do not run the quick verification run
  EOF
    exit 1
  }

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --force) FORCE=true; shift ;;
      --skip-seal) SKIP_SEAL=true; shift ;;
      --skip-build) SKIP_BUILD=true; shift ;;
      --skip-data) SKIP_DATA=true; shift ;;
      --skip-quick) SKIP_QUICK=true; shift ;;
      -h|--help) usage ;;
      *) echo "Unknown arg: $1"; usage ;;
    esac
  done

  info() { echo "[INFO] $*"; }
  warn() { echo "[WARN] $*"; }
  err() { echo "[ERROR] $*" >&2; }

  NPROC="$(nproc 2>/dev/null || echo 1)"
  info "Root: $ROOT_DIR" "CPUs: $NPROC"

  # Decide SEAL install dir (local by default)
  SEAL_DIR_ENV="${SEAL_DIR:-}"
  LOCAL_SEAL_DIR="$ROOT_DIR/thirdparty/seal_install"
  SEAL_CMAKE_DIR=""

  if [ -n "$SEAL_DIR_ENV" ]; then
    info "Using SEAL_DIR from environment: $SEAL_DIR_ENV"
    SEAL_CMAKE_DIR="$SEAL_DIR_ENV/lib/cmake/SEAL-4.1"
  fi

  if [ -z "$SEAL_CMAKE_DIR" ] && [ -d "$LOCAL_SEAL_DIR/lib/cmake/SEAL-4.1" ]; then
    info "Found existing local SEAL install at $LOCAL_SEAL_DIR"
    SEAL_CMAKE_DIR="$LOCAL_SEAL_DIR/lib/cmake/SEAL-4.1"
  fi

  if [ -z "$SEAL_CMAKE_DIR" ] && [ -d "/usr/local/lib/cmake/SEAL-4.1" ]; then
    info "Found system SEAL at /usr/local"
    SEAL_CMAKE_DIR="/usr/local/lib/cmake/SEAL-4.1"
  fi

  # 1) Build SEAL locally (no sudo) unless instructed to skip or already present
  if [ "$SKIP_SEAL" = true ]; then
    info "Skipping SEAL build by request (--skip-seal)"
  else
    if [ -n "$SEAL_CMAKE_DIR" ] && [ "$FORCE" = false ]; then
      info "SEAL already available at: $SEAL_CMAKE_DIR (skipping build)"
    else
      info "Building Microsoft SEAL locally into: $LOCAL_SEAL_DIR"
      if [ ! -d "$ROOT_DIR/SEAL" ]; then
        info "Cloning SEAL source..."
        git clone --depth 1 https://github.com/microsoft/SEAL.git SEAL
      else
        info "SEAL source exists; using $ROOT_DIR/SEAL"
      fi

      pushd SEAL >/dev/null
      mkdir -p build && cd build
      cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$LOCAL_SEAL_DIR" ..
      info "Compiling and installing SEAL (this may take several minutes)..."
      cmake --build . --target install -j"$NPROC"
      popd >/dev/null

      if [ -d "$LOCAL_SEAL_DIR/lib/cmake/SEAL-4.1" ]; then
        info "SEAL installed to $LOCAL_SEAL_DIR"
        SEAL_CMAKE_DIR="$LOCAL_SEAL_DIR/lib/cmake/SEAL-4.1"
      else
        err "SEAL build finished but install directory not found: $LOCAL_SEAL_DIR/lib/cmake/SEAL-4.1"
        exit 1
      fi
    fi
  fi

  # 2) Configure and build this project using detected SEAL
  if [ "$SKIP_BUILD" = true ]; then
    info "Skipping project build (--skip-build)"
  else
    # If pprag_core already built and not forced, skip build
    EXIST_SO="$(ls build/pprag_core*.so 2>/dev/null || true)"
    if [ -n "$EXIST_SO" ] && [ "$FORCE" = false ]; then
      info "Found existing pprag_core build artifacts; skipping build"
    else
      info "Configuring project with SEAL CMake dir: ${SEAL_CMAKE_DIR:-<not-set>}"
      mkdir -p build
      if [ -n "$SEAL_CMAKE_DIR" ]; then
        cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DSEAL_DIR="$SEAL_CMAKE_DIR"
      else
        warn "SEAL CMake dir not set; attempting configure without explicit SEAL_DIR"
        cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
      fi
      info "Building project..."
      cmake --build build -j"$NPROC"
    fi
  fi

  # 3) Copy pprag_core extension to repo root so "import pprag_core" works without PYTHONPATH
  SO_SRC="$(ls build/pprag_core*.so 2>/dev/null || true)"
  if [ -n "$SO_SRC" ]; then
    info "Copying $SO_SRC -> $ROOT_DIR/pprag_core.so"
    cp -f "$SO_SRC" "$ROOT_DIR/pprag_core.so"
  else
    warn "Built pprag_core extension not found in build/; you may need to run the build step"
  fi

  # 4) Generate small dataset if missing (unless skipped)
  if [ "$SKIP_DATA" = true ]; then
    info "Skipping data generation (--skip-data)"
  else
    if [ ! -f "$ROOT_DIR/data/vectors_100k_768d.npy" ]; then
      info "Generating 100k test dataset..."
      PYTHONPATH=build python3 scripts/01_generate_data.py --scales 100k
    else
      info "Dataset ./data/vectors_100k_768d.npy already exists; skipping generation"
    fi
  fi

  # 5) Optional quick verification run (uses sample mode from config)
  if [ "$SKIP_QUICK" = true ]; then
    info "Skipping quick verification run (--skip-quick)"
  else
    info "Running quick verification run (sample mode) to validate the build..."
    set +e
    PYTHONPATH=build python3 scripts/05_run_all.py
    RC=$?
    set -e
    if [ $RC -ne 0 ]; then
      warn "Quick run returned non-zero exit ($RC). You can inspect logs or run the script manually: PYTHONPATH=build python3 scripts/05_run_all.py"
    else
      info "Quick verification run completed successfully"
    fi
  fi

  cat <<EOF
  Bootstrap complete.
  Notes:
  - If you want the extension installed system-wide, build SEAL with sudo and install the pprag_core extension into your Python site-packages.

  To run the benchmark now (uses built extension in build/):
    PYTHONPATH=build python3 scripts/05_run_all.py

  Or run without PYTHONPATH if the script copied the extension to repo root:
    python3 scripts/05_run_all.py
  EOF
