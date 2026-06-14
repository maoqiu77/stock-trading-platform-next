#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-v0.1.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT/dist"
ARCHIVE="$DIST_DIR/stock-trading-platform-next-${VERSION}.zip"

mkdir -p "$DIST_DIR"
rm -f "$ARCHIVE"

cd "$ROOT"

python3 scripts/check_public_safety.py
python3 scripts/check_release_readiness.py

zip -r "$ARCHIVE" . \
  -x ".git/*" \
  -x "*/.git/*" \
  -x "*/.git/**" \
  -x "dist/*" \
  -x "node_modules/*" \
  -x "apps/web/node_modules/*" \
  -x "apps/web/.next/*" \
  -x ".venv/*" \
  -x "storage/local/*" \
  -x "*.db" \
  -x "*.sqlite" \
  -x "*.sqlite3" \
  -x ".env" \
  -x ".env.*" \
  -x "apps/**/.env" \
  -x "apps/**/.env.*" \
  -x ".DS_Store" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*"

echo "$ARCHIVE"
