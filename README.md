# iperf3 GUI

A simple **Windows and Linux desktop app** for **[iperf3](https://github.com/esnet/iperf)** — the standard tool for measuring **how fast your network really is** (upload, download, UDP, and more).

---

## What is iperf3?

**iperf3** runs a controlled test between two computers: one side is the **client**, the other is the **server**. It reports **throughput** (e.g. Mbits/sec) so you can check your ISP, Wi‑Fi, VPN, or a link to another site.

Normally you use iperf3 in a **terminal** and remember flags like `-c`, `-p`, `-t`, `-R`, `-u`, etc. That works well for experts, but it is **easy to mistype** and **hard for people who do not live in the command line**.

---

## Why we built this GUI

| Without this app | With this app |
|------------------|---------------|
| Open a terminal, type long commands | Pick a **region** and a **preset**, click **Run** |
| Look up which **public test servers** exist and which **ports** they use | Presets include known public hosts (use politely) |
| Copy errors from a black window | **Results** stay in one scrollable window |
| Install **iperf3** yourself (Windows: winget / download; Linux: package manager) | **Windows:** **Fetch iperf3** can download a build next to the app. **Linux:** install `iperf3` once with `apt`/`dnf`/… |
| Advanced users still want **every** iperf3 option | **Manual** mode: paste the **same arguments** you would use on the command line |

In short: **the GUI does not replace iperf3** — it **starts iperf3 for you**, builds the right command (or runs exactly what you paste), and **shows the output clearly**. Experts keep full control; everyone else gets a gentler path to real measurements.

---

## Requirements

- **Windows** or **Linux** (with **tkinter** — on Debian/Ubuntu: `sudo apt install python3-tk`).
- **Python 3.11+** only if you run **from source**.
- **iperf3** on your PATH (Linux: `sudo apt install iperf3` or your distro equivalent). **Windows:** PATH, or **Fetch iperf3** in the app ([ar51an build](https://github.com/ar51an/iperf3-win-builds)).

---

## Run from source

**Windows**

```powershell
python iperf3_gui.py
```

**Linux**

```bash
python3 iperf3_gui.py
```

---

## Build portable Windows EXE and MSI

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

Outputs (not stored in git):

- `dist\iperf3-gui.exe`
- `dist\iperf3-gui-<version>-win64.msi` (uninstall via **Settings → Apps**)

If the script says the `.exe` is in use, **close iperf3 GUI** and run again.

---

## Build Linux single binary (on Linux)

On a Linux machine (or WSL with X11/Wayland for the GUI):

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Produces **`dist/iperf3-gui`** (executable, no `.exe`). You need **python3-tk** installed to **run** the app (`apt install python3-tk`).

### CI / GitHub Releases

Pushing a **git tag** like `v1.1.1` runs [`.github/workflows/build-linux.yml`](.github/workflows/build-linux.yml) on **Ubuntu** and uploads a **workflow artifact** you can attach to a GitHub Release (alongside the Windows `.exe` / `.msi` built locally or on another workflow).

---

## Version

Same version in `iperf3_gui.py` (`__version__`) and `freeze_setup.py` (`version=`). See [CHANGELOG.md](CHANGELOG.md) and [RELEASING.md](RELEASING.md).

---

## License

[LICENSE](LICENSE) (MIT).
