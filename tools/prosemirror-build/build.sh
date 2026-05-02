#!/usr/bin/env bash
set -euo pipefail

# Build the ProseMirror bundle vendored into Genropy.
# Output: ../../resources/js_libs/prosemirror/prosemirror.bundle.js (+ sourcemap)
#
# Usage:
#   cd tools/prosemirror-build
#   ./build.sh

cd "$(dirname "$0")"

TARGET_DIR="../../resources/js_libs/prosemirror"
mkdir -p "$TARGET_DIR"

if [ -f package-lock.json ]; then
    npm ci
else
    npm install
fi

npm run build

# Concatenate the upstream stylesheets into a single vendored CSS file. Both are
# tiny (a few dozen lines each) and required for proper rendering: prosemirror.css
# carries the white-space rules expected by EditorView, gapcursor.css styles the
# blinking gap cursor between block nodes.
CSS_OUT="$TARGET_DIR/prosemirror.css"
{
    echo "/* Vendored stylesheets concatenated by tools/prosemirror-build/build.sh */"
    echo "/* Source: prosemirror-view, gapcursor, menu, example-setup, tables. */"
    cat node_modules/prosemirror-view/style/prosemirror.css
    cat node_modules/prosemirror-gapcursor/style/gapcursor.css
    cat node_modules/prosemirror-menu/style/menu.css
    cat node_modules/prosemirror-example-setup/style/style.css
    cat node_modules/prosemirror-tables/style/tables.css
    cat <<'GNRCSS'

/* Genropy overrides: keep readonly editors selectable. ProseMirror flips
 * contenteditable to "false" when editable() returns false; some browsers
 * then refuse text selection in nested elements. Force user-select: text on
 * the whole container so users can still copy content from a readonly view. */
.ProseMirror[contenteditable="false"],
.ProseMirror[contenteditable="false"] * {
    -webkit-user-select: text;
    -moz-user-select: text;
    user-select: text;
}
GNRCSS
} > "$CSS_OUT"

echo
echo "Build complete:"
ls -lh "$TARGET_DIR"
