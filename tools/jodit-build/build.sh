#!/usr/bin/env bash
set -euo pipefail

# Vendor the pinned Jodit distribution into Genropy.
# Output: ../../resources/js_libs/jodit/{jodit.min.js,jodit.min.css,LICENSE.txt}
#
# Usage:
#   cd tools/jodit-build
#   ./build.sh

cd "$(dirname "$0")"

TARGET_DIR="../../resources/js_libs/jodit"
mkdir -p "$TARGET_DIR"

if [ -f package-lock.json ]; then
    npm ci
else
    npm install
fi

DIST="node_modules/jodit/es2021"
cp "$DIST/jodit.min.js" "$TARGET_DIR/jodit.min.js"
cp node_modules/jodit/LICENSE.txt "$TARGET_DIR/LICENSE.txt"

CSS_OUT="$TARGET_DIR/jodit.min.css"
{
    cat "$DIST/jodit.min.css"
    cat <<'GNRCSS'

/* Genropy overrides, appended by tools/jodit-build/build.sh */
.gnr-jodit-host {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
}
.gnr-jodit-host > .jodit-container:not(.jodit_fullsize) {
    flex: 1 1 auto;
    min-height: 0;
}
.jodit-source .gnr-jodit-codemirror {
    height: 100%;
}
.jodit-source .gnr-jodit-codemirror .cm-editor {
    height: 100%;
    background: #fff;
    color: #222;
}
GNRCSS
} > "$CSS_OUT"

echo
echo "Build complete:"
ls -lh "$TARGET_DIR"
