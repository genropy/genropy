#!/usr/bin/env bash
set -euo pipefail

# Build the CodeMirror 6 bundle vendored into Genropy.
# Output: ../../genropy/resources/js_libs/codemirror6/codemirror6.bundle.js (+ sourcemap)
#
# Usage:
#   cd tools/codemirror6-build
#   ./build.sh

cd "$(dirname "$0")"

# Ensure target dir exists.
TARGET_DIR="../../resources/js_libs/codemirror6"
mkdir -p "$TARGET_DIR"

# Install deps from lockfile when available, otherwise resolve fresh.
if [ -f package-lock.json ]; then
    npm ci
else
    npm install
fi

# Run the bundle.
npm run build

echo
echo "Build complete:"
ls -lh "$TARGET_DIR"
