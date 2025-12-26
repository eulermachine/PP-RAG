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
