# iperf3 GUI

Windows desktop app for **[iperf3](https://github.com/esnet/iperf)** network throughput tests: guided presets (regions and public servers) or **manual** mode with the same flags as the real CLI.

## Requirements

- **Windows** (primary target).
- **Python 3.11+** if you run from source.
- **iperf3** on PATH, or use **Fetch iperf3** in the app (downloads the [ar51an Windows build](https://github.com/ar51an/iperf3-win-builds) next to the app).

## Run from source

```powershell
python iperf3_gui.py
```

## Build portable EXE and MSI

From this directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

Outputs (not committed to git):

- `dist\iperf3-gui.exe` — single-file GUI
- `dist\iperf3-gui-<version>-win64.msi` — installer (uninstall via **Settings → Apps**)

Close a running `iperf3-gui.exe` before rebuilding if the script warns the file is locked.

## Version

Application version is `__version__` in `iperf3_gui.py` and should match `version` in `freeze_setup.py`. See `CHANGELOG.md` and `RELEASING.md`.

## License

See [LICENSE](LICENSE).
