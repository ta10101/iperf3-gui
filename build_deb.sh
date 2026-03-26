#!/usr/bin/env bash
# Build a Debian/Ubuntu .deb installer (amd64/arm64) with the PyInstaller binary inside.
# Run on Linux. Requires: dpkg-deb, python3, PyInstaller (build_linux.sh installs it).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
OUT="$ROOT/dist"
STAGE="$OUT/deb_staging"

extract_version() {
  grep -E '^__version__\s*=' "$ROOT/iperf3_gui.py" | head -1 | sed -E 's/.*=\s*["'\'']//;s/["'\''].*//'
}

VERSION="$(extract_version)"
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
esac

DEB_NAME="iperf3-gui_${VERSION}_${ARCH}.deb"

if [[ ! -f "$OUT/iperf3-gui" ]]; then
  echo "=== No dist/iperf3-gui — running build_linux.sh first ==="
  bash "$ROOT/build_linux.sh"
fi

if [[ ! -f "$OUT/iperf3-gui" ]]; then
  echo "ERROR: dist/iperf3-gui missing after build."
  exit 1
fi

if ! command -v dpkg-deb >/dev/null; then
  echo "ERROR: dpkg-deb not found. On Debian/Ubuntu: sudo apt install dpkg-dev"
  exit 1
fi

echo "=== Building $DEB_NAME ==="
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/doc/iperf3-gui"

cp "$OUT/iperf3-gui" "$STAGE/usr/bin/iperf3-gui"
chmod 755 "$STAGE/usr/bin/iperf3-gui"

cat > "$STAGE/DEBIAN/control" << EOF
Package: iperf3-gui
Version: ${VERSION}
Section: net
Priority: optional
Architecture: ${ARCH}
Depends: libc6 (>= 2.31)
Recommends: iperf3
Maintainer: iperf3-gui contributors <iperf3-gui@users.noreply.github.com>
Description: graphical interface for iperf3 network testing
 Wraps the standard iperf3 tool with guided presets, public server
 lists, and a manual mode for full CLI compatibility. Install the
 recommended iperf3 package to run tests (or use a custom binary path).
EOF

cat > "$STAGE/usr/share/applications/iperf3-gui.desktop" << 'EOF'
[Desktop Entry]
Name=iperf3 GUI
Comment=Network throughput tests with iperf3
Exec=iperf3-gui
Icon=network-workgroup
Terminal=false
Type=Application
Categories=Network;Utility;
Keywords=network;iperf;speedtest;bandwidth;
EOF

cp "$ROOT/LICENSE" "$STAGE/usr/share/doc/iperf3-gui/copyright" 2>/dev/null || true

cat > "$STAGE/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q 2>/dev/null || true
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q 2>/dev/null || true
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postrm"

rm -f "$OUT/$DEB_NAME"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT/$DEB_NAME"
rm -rf "$STAGE"

echo ""
echo "Done: $OUT/$DEB_NAME"
echo "Install: sudo apt install ./$DEB_NAME"
echo "   or:   sudo dpkg -i $OUT/$DEB_NAME && sudo apt-get install -f"
