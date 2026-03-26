#!/usr/bin/env bash
# Build a single-file Linux GUI binary with PyInstaller (run on Linux or in CI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Install deps (Debian/Ubuntu example) ==="
echo "If tkinter is missing: sudo apt install python3-tk python3-venv"
echo "iperf3 for local tests: sudo apt install iperf3"
echo ""

python3 -m pip install --user --upgrade pip
python3 -m pip install --user "pyinstaller>=6.0"

OUT="$ROOT/dist"
rm -f "$OUT/iperf3-gui-new" "$OUT/iperf3-gui" 2>/dev/null || true
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "iperf3-gui-new" \
  --onefile \
  --distpath "$OUT" \
  iperf3_gui.py

if [[ -f "$OUT/iperf3-gui-new" ]]; then
  rm -f "$OUT/iperf3-gui"
  mv "$OUT/iperf3-gui-new" "$OUT/iperf3-gui"
  chmod +x "$OUT/iperf3-gui"
  echo ""
  echo "Done: $OUT/iperf3-gui"
  echo "Run:  $OUT/iperf3-gui"
fi
