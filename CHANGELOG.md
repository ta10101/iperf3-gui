# Changelog

## 1.1.2 — 2026-03-26

### Added
- **Debian/Ubuntu `.deb` package** via `build_deb.sh`: installs `iperf3-gui` to `/usr/bin`, desktop entry, recommends `iperf3`.
- CI uploads the `.deb` together with the raw Linux binary.

## 1.1.1 — 2026-03-26

### Added
- **Linux**: same GUI via tkinter; `iperf3` from PATH / package manager (`apt` / `dnf` / etc.).
- **`build_linux.sh`**: local PyInstaller one-file build on Linux.
- **GitHub Actions** (`.github/workflows/build-linux.yml`): builds `dist/iperf3-gui` on Ubuntu on each `v*` tag (artifact download for releases).

### Changed
- Help menu and “not ready” hints are platform-specific (Windows MSI vs Linux packages).

## 1.1.0 — 2026-03-26

### Added
- Guided mode: regions (Europe, North America, Asia-Pacific, Latin America), public server presets, test presets.
- Manual mode: paste any iperf3 CLI arguments; optional stripping of a leading `iperf3` token.
- Extra iperf3 flags in guided mode: IPv6 (`-6`), JSON (`-J`), bidirectional (`--bidir`), TCP no delay (`-N`), interval (`-i`), window (`-w`), and a free-form “Extra args” field.
- Busy public servers: optional rotation across extra ports when the server reports busy.
- Optional download of `iperf3.exe` (ar51an build) next to the app; PATH detection.
- Help menu: `iperf3 --help`, open Windows Apps (uninstall), remove local downloaded `iperf3.exe`.
- Windows packaging: `build_release.ps1` (PyInstaller portable EXE + cx_Freeze MSI), Start menu shortcut on MSI install.

### Notes
- Source distribution contains no personal paths; do not commit `dist/`, `build/`, or `*.spec`.
- Runtime: speed tests contact third-party hosts; “Fetch iperf3” uses GitHub over HTTPS.
