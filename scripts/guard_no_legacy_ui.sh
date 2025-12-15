#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/src"

if [[ ! -d "$SRC" ]]; then
  echo "[guard] FAIL: missing src dir: $SRC" >&2
  exit 1
fi

forbidden=(
  "dashboard"
  "card"
  "cards"
  "panel"
  "panels"
  "sidebar"
  "sidebars"
  "dock"
  "docked"
  "windowing"
)

for term in "${forbidden[@]}"; do
  if grep -R -n -i -E "\\b${term}\\b" "$SRC" >/dev/null 2>&1; then
    echo "[guard] FAIL: legacy UI term found in src: ${term}" >&2
    grep -R -n -i -E "\\b${term}\\b" "$SRC" | head -n 20 >&2 || true
    exit 1
  fi
done

if grep -R -n -i -E "setinterval\\s*\\(" "$SRC" >/dev/null 2>&1; then
  echo "[guard] FAIL: setInterval-style refresh loop found in src" >&2
  grep -R -n -i -E "setinterval\\s*\\(" "$SRC" | head -n 20 >&2 || true
  exit 1
fi

echo "[guard] OK: no legacy UI terms detected"

