"""
Simple Windows GUI for iperf3 (network throughput testing).
Requires iperf3.exe — e.g. from https://github.com/ar51an/iperf3-win-builds

EU server names are curated from public lists (e.g. R0GGER/public-iperf3-servers);
third-party servers may change or rate-limit — use politely.
"""

from __future__ import annotations

__version__ = "1.1.0"

import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
import zipfile
from dataclasses import dataclass
from tkinter import filedialog, messagebox, scrolledtext, ttk


# Official Windows build (pinned); used when no local copy is found.
IPERF3_WIN_ZIP_URL = (
    "https://github.com/ar51an/iperf3-win-builds/releases/download/3.20/iperf-3.20-win64.zip"
)


def _application_directory() -> str:
    """Directory where the app lives (installer folder or script folder, not PyInstaller temp)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _no_window_flags() -> int:
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return 0


def _verify_iperf3_cli(path: str) -> bool:
    if not path or not os.path.isfile(path):
        return False
    try:
        r = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=_no_window_flags(),
            stdin=subprocess.DEVNULL,
        )
        out = ((r.stdout or "") + (r.stderr or "")).lower()
        return r.returncode == 0 and "iperf" in out
    except (OSError, subprocess.TimeoutExpired):
        return False


def _download_iperf3_windows(app_dir: str) -> bool:
    """Download ar51an iperf3 zip and extract iperf3.exe into app_dir. Returns True if verified."""
    dest = os.path.join(app_dir, "iperf3.exe")
    partial = dest + ".partial"
    try:
        req = urllib.request.Request(
            IPERF3_WIN_ZIP_URL,
            headers={"User-Agent": "iperf3-gui"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(data)
            zip_path = tmp.name
        try:
            with zipfile.ZipFile(zip_path) as zf:
                member = None
                for name in zf.namelist():
                    base = name.replace("\\", "/").split("/")[-1]
                    if base.lower() == "iperf3.exe":
                        member = name
                        break
                if not member:
                    return False
                with zf.open(member) as src, open(partial, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            os.replace(partial, dest)
        finally:
            try:
                os.unlink(zip_path)
            except OSError:
                pass
            try:
                if os.path.isfile(partial):
                    os.unlink(partial)
            except OSError:
                pass
        return _verify_iperf3_cli(dest)
    except Exception:
        try:
            if os.path.isfile(partial):
                os.unlink(partial)
        except OSError:
            pass
        return False


def resolve_iperf3_executable(app_dir: str) -> tuple[str, str, bool]:
    """
    Pick a working iperf3 before the UI runs tests.
    Returns (path for the field, short status line, verified_ok).
    """
    bundled = os.path.join(app_dir, "iperf3.exe")

    if os.path.isfile(bundled):
        if _verify_iperf3_cli(bundled):
            return bundled, "Ready — using iperf3.exe next to this app.", True
        try:
            os.remove(bundled)
        except OSError:
            pass

    for cmd in ("iperf3.exe", "iperf3"):
        found = shutil.which(cmd)
        if found and os.path.isfile(found) and _verify_iperf3_cli(found):
            return os.path.normpath(found), f"Ready — using iperf3 from PATH ({found}).", True

    if sys.platform == "win32":
        if _download_iperf3_windows(app_dir) and os.path.isfile(bundled):
            if _verify_iperf3_cli(bundled):
                return bundled, "Ready — downloaded iperf3.exe into this folder (first run).", True

    fallback = "iperf3"
    return (
        fallback,
        "iperf3 not ready — click “Fetch iperf3” or Browse, or install: winget install ar51an.iPerf3",
        False,
    )


@dataclass(frozen=True)
class EuServerPreset:
    """Single default port plus optional inclusive range used when a port is 'busy'."""

    title: str
    host: str
    port: str
    note: str = ""
    port_retry_low: int | None = None
    port_retry_high: int | None = None


# Curated EU-focused public servers (host + one port from documented ranges).
EU_SERVER_PRESETS: list[EuServerPreset] = [
    EuServerPreset(
        "France — Paris (Scaleway)",
        "ping.online.net",
        "5201",
        "Popular; shared — 'busy' is common; we rotate 5200–5209.",
        5200,
        5209,
    ),
    EuServerPreset(
        "France — Paris (online.net alt)",
        "iperf.online.net",
        "5201",
        "",
        5200,
        5209,
    ),
    EuServerPreset(
        "Germany — Frankfurt (Leaseweb)",
        "speedtest.fra1.de.leaseweb.net",
        "5201",
        "",
        5201,
        5210,
    ),
    EuServerPreset(
        "Germany — Frankfurt (Clouvider)",
        "fra.speedtest.clouvider.net",
        "5201",
        "",
        5200,
        5209,
    ),
    EuServerPreset(
        "Netherlands — Amsterdam (Leaseweb)",
        "speedtest.ams1.nl.leaseweb.net",
        "5201",
        "",
        5201,
        5210,
    ),
    EuServerPreset(
        "Netherlands — Amsterdam (Clouvider)",
        "ams.speedtest.clouvider.net",
        "5201",
        "",
        5200,
        5209,
    ),
    EuServerPreset("Spain — Madrid", "185.93.3.50", "5201", ""),
    EuServerPreset("Italy — Milan", "84.17.59.129", "5201", ""),
    EuServerPreset("Sweden — Stockholm", "185.76.9.135", "5201", ""),
    EuServerPreset("Poland — Warsaw", "185.246.208.67", "5201", ""),
    EuServerPreset("Austria — Vienna", "185.180.12.40", "5201", ""),
    EuServerPreset("Belgium — Brussels", "207.211.214.65", "5201", ""),
    EuServerPreset("Czechia — Prague", "185.152.65.113", "5201", ""),
    EuServerPreset("Denmark — Copenhagen", "121.127.45.65", "5201", ""),
    EuServerPreset(
        "Finland — Helsinki",
        "spd-fisrv.hostkey.com",
        "5201",
        "Range 5201–5209.",
        5201,
        5209,
    ),
    EuServerPreset("Ireland — Dublin", "87.249.137.8", "5201", ""),
    EuServerPreset("Portugal — Lisbon", "109.61.94.65", "5201", ""),
    EuServerPreset("Romania — Bucharest", "185.102.217.170", "5201", ""),
    EuServerPreset("Greece — Athens", "169.150.252.2", "5201", ""),
    EuServerPreset(
        "Estonia — Tallinn",
        "bwtest.linxtelecom.com",
        "5201",
        "Range 5201–5209.",
        5201,
        5209,
    ),
    EuServerPreset("Slovakia — Bratislava", "156.146.40.65", "5201", ""),
    EuServerPreset("Croatia — Zagreb", "169.150.242.129", "5201", ""),
    EuServerPreset("Bulgaria — Sofia", "37.19.203.1", "5201", ""),
]

REGION_PRESETS: dict[str, list[EuServerPreset]] = {
    "Europe": EU_SERVER_PRESETS,
    "North America": [
        EuServerPreset(
            "US — Chicago (Clouvider)",
            "ord.speedtest.clouvider.net",
            "5201",
            "",
            5200,
            5209,
        ),
        EuServerPreset(
            "US — NYC (Leaseweb)",
            "speedtest.nyc2.us.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "US — Miami (Leaseweb)",
            "speedtest.mia2.us.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "CA — Montreal (Leaseweb)",
            "speedtest.mtl2.ca.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "US — Ashburn (Leaseweb)",
            "speedtest.wdc2.us.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
    ],
    "Asia-Pacific": [
        EuServerPreset(
            "JP — Tokyo (Leaseweb)",
            "speedtest.tyo11.jp.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "SG — Singapore (Leaseweb)",
            "speedtest.sin1.sg.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "HK — Hong Kong (Leaseweb)",
            "speedtest.hkg12.hk.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
        EuServerPreset(
            "AU — Sydney (Leaseweb)",
            "speedtest.syd7.au.leaseweb.net",
            "5201",
            "",
            5201,
            5210,
        ),
    ],
    "Latin America": [
        EuServerPreset(
            "BR — São Paulo",
            "138.199.4.1",
            "5201",
            "",
        ),
    ],
}

REGION_NAMES = list(REGION_PRESETS.keys())

CUSTOM_SERVER_LABEL = "Custom — type host & port below"


def _iter_all_server_presets() -> list[EuServerPreset]:
    out: list[EuServerPreset] = []
    for lst in REGION_PRESETS.values():
        out.extend(lst)
    return out


@dataclass(frozen=True)
class TestPreset:
    title: str
    hint: str
    seconds: str
    parallel: str
    udp: bool
    reverse: bool
    bandwidth: str
    ipv6: bool = False
    json_out: bool = False
    bidir: bool = False
    interval: str = ""
    tcp_nodelay: bool = False


TEST_PRESETS: list[TestPreset] = [
    TestPreset(
        "Download speed (best for most public servers)",
        "Uses reverse mode: data flows toward your PC. Matches how many EU public servers expect to be used.",
        "15",
        "1",
        False,
        True,
        "100M",
    ),
    TestPreset(
        "Quick download check (10 seconds)",
        "Short run; good to see if the server responds.",
        "10",
        "1",
        False,
        True,
        "100M",
    ),
    TestPreset(
        "Long download (60 seconds)",
        "More stable average on busy links.",
        "60",
        "1",
        False,
        True,
        "100M",
    ),
    TestPreset(
        "Fast line — 4 parallel downloads",
        "Helps saturate higher-speed connections (reverse mode).",
        "20",
        "4",
        False,
        True,
        "100M",
    ),
    TestPreset(
        "Upload speed (may fail on some public hosts)",
        "Sends from your PC to the server. Some public servers only allow reverse tests.",
        "15",
        "1",
        False,
        False,
        "100M",
    ),
    TestPreset(
        "UDP check at 100 Mbps (download-style)",
        "UDP with reverse mode; jitter/loss shown in output.",
        "15",
        "1",
        True,
        True,
        "100M",
    ),
    TestPreset(
        "UDP at 1 Gbps (download-style)",
        "High UDP target rate; adjust if your line is slower.",
        "15",
        "1",
        True,
        True,
        "1G",
    ),
    TestPreset(
        "JSON summary (-J)",
        "Machine-readable summary line at the end (good for logging).",
        "10",
        "1",
        False,
        True,
        "100M",
        json_out=True,
    ),
    TestPreset(
        "Bidirectional (--bidir)",
        "Measures both directions in one run.",
        "15",
        "1",
        False,
        False,
        "100M",
        bidir=True,
    ),
    TestPreset(
        "IPv6 download (-6, -R)",
        "Requires IPv6 to the host and iperf3 IPv6 support.",
        "15",
        "1",
        False,
        True,
        "100M",
        ipv6=True,
    ),
    TestPreset(
        "Stats every second (-i 1)",
        "More lines in the output during the test.",
        "15",
        "1",
        False,
        True,
        "100M",
        interval="1",
    ),
    TestPreset(
        "TCP no delay (-N)",
        "Disables Nagle (lower latency, often lower goodput on long paths).",
        "15",
        "1",
        False,
        True,
        "100M",
        tcp_nodelay=True,
    ),
    TestPreset(
        "Custom — keep my settings below",
        "Does not change duration, streams, UDP, or reverse; only pick this after adjusting the form.",
        "",  # sentinel: do not overwrite option fields
        "",
        False,
        False,
        "",
    ),
]


class Iperf3GUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"iperf3 GUI v{__version__}")
        self.minsize(720, 620)
        self.geometry("860x780")

        self._proc: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._out_queue: queue.Queue[str | None] = queue.Queue()

        self._app_dir = _application_directory()
        exe_path, exe_status, self._iperf3_ready = resolve_iperf3_executable(self._app_dir)
        self.exe_var = tk.StringVar(value=exe_path)
        self._exe_status_var = tk.StringVar(value=exe_status)
        self.mode_var = tk.StringVar(value="client")
        self.host_var = tk.StringVar(value=EU_SERVER_PRESETS[0].host)
        self.port_var = tk.StringVar(value=EU_SERVER_PRESETS[0].port)
        self.time_var = tk.StringVar(value="15")
        self.parallel_var = tk.StringVar(value="1")
        self.bind_var = tk.StringVar(value="")
        self.udp_var = tk.BooleanVar(value=False)
        self.reverse_var = tk.BooleanVar(value=True)
        self.bandwidth_var = tk.StringVar(value="100M")
        self.retry_busy_var = tk.BooleanVar(value=True)
        self.region_var = tk.StringVar(value="Europe")
        self.command_mode_var = tk.StringVar(value="guided")
        self.ipv6_var = tk.BooleanVar(value=False)
        self.json_var = tk.BooleanVar(value=False)
        self.bidir_var = tk.BooleanVar(value=False)
        self.tcp_nodelay_var = tk.BooleanVar(value=False)
        self.interval_var = tk.StringVar(value="")
        self.window_var = tk.StringVar(value="")
        self.extra_args_var = tk.StringVar(value="")

        self._run_cancel = threading.Event()
        self._client_worker: threading.Thread | None = None

        self.server_preset_var = tk.StringVar()
        self.test_preset_var = tk.StringVar()
        self.hint_var = tk.StringVar(value=TEST_PRESETS[0].hint)

        self._easy_frame: ttk.LabelFrame | None = None
        self._server_combo: ttk.Combobox | None = None
        self._test_combo: ttk.Combobox | None = None
        self._region_combo: ttk.Combobox | None = None
        self._guided_frame: ttk.Frame | None = None
        self._manual_frame: ttk.Frame | None = None
        self.manual_cmd: scrolledtext.ScrolledText | None = None

        self._build_ui()
        self._fill_preset_combos()
        self.command_mode_var.trace_add("write", self._on_command_mode_change)
        self.mode_var.trace_add("write", self._on_mode_change)
        self.after(100, self._drain_output_queue)
        self._on_mode_change()
        if not self._iperf3_ready:
            self.after(300, self._warn_iperf3_not_ready)
        self._on_command_mode_change()

    def _build_menubar(self) -> None:
        mbar = tk.Menu(self)
        self.config(menu=mbar)
        help_m = tk.Menu(mbar, tearoff=0)
        mbar.add_cascade(label="Help", menu=help_m)
        help_m.add_command(label="Show iperf3 --help", command=self._show_iperf_help)
        help_m.add_command(label="Uninstall (open Windows Apps settings)", command=self._open_apps_settings_for_uninstall)
        help_m.add_separator()
        help_m.add_command(
            label="Remove downloaded iperf3.exe next to this app",
            command=self._remove_bundled_iperf3_exe,
        )

    def _show_iperf_help(self) -> None:
        exe = self.exe_var.get().strip()
        if not exe:
            messagebox.showerror("iperf3", "Set the iperf3 program path first.")
            return
        path = exe if os.path.isfile(exe) else (shutil.which(exe) or exe)
        try:
            r = subprocess.run(
                [path, "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=_no_window_flags(),
                stdin=subprocess.DEVNULL,
            )
            text = (r.stdout or "") + (r.stderr or "")
        except OSError as e:
            messagebox.showerror("iperf3", str(e))
            return
        win = tk.Toplevel(self)
        win.title("iperf3 --help")
        win.geometry("720x520")
        st = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 9))
        st.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        st.insert(tk.END, text or "(no output)")
        st.configure(state=tk.DISABLED)

    def _open_apps_settings_for_uninstall(self) -> None:
        try:
            os.startfile("ms-settings:appsfeatures")  # type: ignore[attr-defined]
        except OSError:
            messagebox.showinfo(
                "Uninstall",
                "Open Windows Settings → Apps → Installed apps, find iperf3 GUI, then Uninstall.\n"
                "(MSI installs register there automatically.)",
            )

    def _remove_bundled_iperf3_exe(self) -> None:
        p = os.path.join(self._app_dir, "iperf3.exe")
        if not os.path.isfile(p):
            messagebox.showinfo("Remove iperf3.exe", "No iperf3.exe found next to this application.")
            return
        if not messagebox.askyesno(
            "Remove iperf3.exe",
            f"Delete this file?\n{p}",
        ):
            return
        try:
            os.remove(p)
            self._exe_status_var.set("Removed local iperf3.exe. Use Fetch or PATH.")
            messagebox.showinfo("Done", "iperf3.exe was removed.")
        except OSError as e:
            messagebox.showerror("Error", str(e))

    def _warn_iperf3_not_ready(self) -> None:
        messagebox.showwarning(
            "iperf3 not ready",
            "The app could not verify iperf3 on this PC.\n\n"
            'Use “Fetch iperf3” (needs internet), or Browse to iperf3.exe, '
            "or install with:\nwinget install ar51an.iPerf3",
        )

    def _fetch_iperf3(self) -> None:
        if sys.platform != "win32":
            messagebox.showinfo(
                "Fetch iperf3",
                "Automatic download is only set up for Windows.\nInstall iperf3 with your package manager.",
            )
            return
        self._exe_status_var.set("Downloading iperf3…")
        self.update_idletasks()
        ok = _download_iperf3_windows(self._app_dir)
        dest = os.path.join(self._app_dir, "iperf3.exe")
        if ok and os.path.isfile(dest):
            self.exe_var.set(dest)
            self._iperf3_ready = True
            self._exe_status_var.set("Ready — iperf3.exe saved next to this app.")
            messagebox.showinfo("iperf3", "iperf3.exe is installed next to the app and ready to use.")
        else:
            self._exe_status_var.set(
                "Download failed — try again, use Browse, or: winget install ar51an.iPerf3"
            )
            messagebox.showerror(
                "Download failed",
                "Could not download or verify iperf3.\nCheck your connection and try again, "
                "or install manually (winget / Browse).",
            )

    def _fill_preset_combos(self) -> None:
        assert self._server_combo and self._test_combo
        self._fill_server_combo_only()
        self._test_combo["values"] = [p.title for p in TEST_PRESETS]
        self.test_preset_var.set(TEST_PRESETS[0].title)
        self._apply_test_preset_by_title(TEST_PRESETS[0].title, force=True)

    def _fill_server_combo_only(self) -> None:
        assert self._server_combo
        reg = self.region_var.get()
        presets = REGION_PRESETS.get(reg, EU_SERVER_PRESETS)
        self._server_combo["values"] = [p.title for p in presets] + [CUSTOM_SERVER_LABEL]
        self.server_preset_var.set(presets[0].title)
        self._apply_server_preset()

    def _on_region_change(self) -> None:
        self._fill_server_combo_only()

    def _on_mode_change(self, *args: object) -> None:
        if self._easy_frame is None:
            return
        if self.command_mode_var.get() != "guided":
            return
        if self.mode_var.get() == "client":
            self._easy_frame.pack(fill=tk.X, padx=8, pady=4, after=self._mode_frame_anchor)
        else:
            self._easy_frame.pack_forget()

    def _on_command_mode_change(self, *args: object) -> None:
        if self._guided_frame is None or self._manual_frame is None:
            return
        self._guided_frame.pack_forget()
        self._manual_frame.pack_forget()
        if self.command_mode_var.get() == "manual":
            self._manual_frame.pack(fill=tk.BOTH, expand=False, padx=0, pady=0)
        else:
            self._guided_frame.pack(fill=tk.BOTH, expand=False, padx=0, pady=0)
            self._on_mode_change()

    def _build_ui(self) -> None:
        self._build_menubar()
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self)
        top.pack(fill=tk.X, **pad)
        ttk.Label(top, text="iperf3 program:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.exe_var, width=42).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4)
        )
        ttk.Button(top, text="Fetch iperf3", command=self._fetch_iperf3).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(top, text="Browse…", command=self._browse_exe).pack(side=tk.LEFT)

        status = tk.Label(
            self,
            textvariable=self._exe_status_var,
            anchor=tk.W,
            fg="#0a6b0a" if self._iperf3_ready else "#8a5a00",
            font=("Segoe UI", 9),
        )
        status.pack(fill=tk.X, padx=12, pady=(0, 2))

        cmd_mode = ttk.LabelFrame(self, text="How do you want to run iperf3?")
        cmd_mode.pack(fill=tk.X, **pad)
        ttk.Radiobutton(
            cmd_mode,
            text="Guided — regions, presets, and forms (same flags as CLI, built for you)",
            variable=self.command_mode_var,
            value="guided",
        ).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Radiobutton(
            cmd_mode,
            text="Manual — type or paste full iperf3 arguments (exactly like the command line)",
            variable=self.command_mode_var,
            value="manual",
        ).pack(anchor=tk.W, padx=8, pady=2)

        self._body_middle = ttk.Frame(self)
        self._body_middle.pack(fill=tk.X, expand=False)

        self._guided_frame = ttk.Frame(self._body_middle)
        self._guided_frame.pack(fill=tk.X, expand=False)

        mode_frame = ttk.LabelFrame(self._guided_frame, text="Mode")
        mode_frame.pack(fill=tk.X, **pad)
        self._mode_frame_anchor = mode_frame
        ttk.Radiobutton(
            mode_frame, text="Test toward a server (client — usual for home users)", variable=self.mode_var, value="client"
        ).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Radiobutton(
            mode_frame, text="Wait for someone to test to this PC (server)", variable=self.mode_var, value="server"
        ).pack(anchor=tk.W, padx=8, pady=2)

        easy = ttk.LabelFrame(self._guided_frame, text="Easy setup — public servers & test type")
        self._easy_frame = easy

        rr = ttk.Frame(easy)
        rr.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Label(rr, text="Region:").grid(row=0, column=0, sticky=tk.W)
        self._region_combo = ttk.Combobox(
            rr,
            textvariable=self.region_var,
            values=REGION_NAMES,
            state="readonly",
            width=22,
        )
        self._region_combo.grid(row=0, column=1, sticky=tk.W, padx=(6, 16))
        self._region_combo.bind("<<ComboboxSelected>>", lambda e: self._on_region_change())

        er = ttk.Frame(easy)
        er.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(er, text="Server location:").grid(row=0, column=0, sticky=tk.NW, pady=(0, 4))
        self._server_combo = ttk.Combobox(
            er,
            textvariable=self.server_preset_var,
            state="readonly",
            width=48,
        )
        self._server_combo.grid(row=0, column=1, sticky=tk.EW, padx=(6, 0), pady=(0, 4))
        er.columnconfigure(1, weight=1)
        ttk.Button(er, text="Use this server", command=self._apply_server_preset).grid(
            row=0, column=2, padx=(8, 0), pady=(0, 4)
        )

        tr = ttk.Frame(easy)
        tr.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(tr, text="Kind of test:").grid(row=0, column=0, sticky=tk.NW)
        self._test_combo = ttk.Combobox(
            tr,
            textvariable=self.test_preset_var,
            state="readonly",
            width=48,
        )
        self._test_combo.grid(row=0, column=1, sticky=tk.EW, padx=(6, 0))
        tr.columnconfigure(1, weight=1)
        ttk.Button(tr, text="Apply preset", command=self._apply_test_preset_from_ui).grid(row=0, column=2, padx=(8, 0))

        self._server_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_server_preset())
        self._test_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_test_preset_from_ui())

        ttk.Label(
            easy,
            textvariable=self.hint_var,
            wraplength=800,
            justify=tk.LEFT,
            foreground="#333",
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

        ttk.Separator(self._guided_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        opts = ttk.LabelFrame(
            self._guided_frame,
            text="Fine-tune (optional — same options iperf3 accepts on the command line)",
        )
        opts.pack(fill=tk.X, **pad)

        row1 = ttk.Frame(opts)
        row1.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row1, text="Server address (-c host):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(row1, textvariable=self.host_var, width=32).grid(
            row=0, column=1, sticky=tk.W, padx=(4, 12)
        )
        ttk.Label(row1, text="Port (-p):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(row1, textvariable=self.port_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=4)

        row2 = ttk.Frame(opts)
        row2.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row2, text="Length (-t seconds):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(row2, textvariable=self.time_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=(4, 16))
        ttk.Label(row2, text="Parallel (-P):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(row2, textvariable=self.parallel_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=4)

        row3 = ttk.Frame(opts)
        row3.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row3, text="Server bind (-B, server only):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(row3, textvariable=self.bind_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=(4, 12))
        ttk.Checkbutton(row3, text="UDP (-u)", variable=self.udp_var).grid(row=0, column=2, sticky=tk.W, padx=(0, 8))
        ttk.Checkbutton(
            row3,
            text='Reverse (-R)',
            variable=self.reverse_var,
        ).grid(row=0, column=3, sticky=tk.W)

        row3b = ttk.Frame(opts)
        row3b.pack(fill=tk.X, padx=8, pady=4)
        ttk.Checkbutton(row3b, text="IPv6 (-6)", variable=self.ipv6_var).grid(row=0, column=0, sticky=tk.W, padx=(0, 12))
        ttk.Checkbutton(row3b, text="JSON (-J)", variable=self.json_var).grid(row=0, column=1, sticky=tk.W, padx=(0, 12))
        ttk.Checkbutton(row3b, text="Bidir (--bidir)", variable=self.bidir_var).grid(row=0, column=2, sticky=tk.W, padx=(0, 12))
        ttk.Checkbutton(row3b, text="TCP no delay (-N)", variable=self.tcp_nodelay_var).grid(row=0, column=3, sticky=tk.W)

        row4 = ttk.Frame(opts)
        row4.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row4, text="UDP bitrate (-b):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(row4, textvariable=self.bandwidth_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=(4, 16))
        ttk.Label(row4, text="Interval (-i):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(row4, textvariable=self.interval_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=4)
        ttk.Label(row4, text="sec", foreground="gray").grid(row=0, column=4, sticky=tk.W)

        row4b = ttk.Frame(opts)
        row4b.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row4b, text="TCP window (-w):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(row4b, textvariable=self.window_var, width=14).grid(row=0, column=1, sticky=tk.W, padx=(4, 8))
        ttk.Label(row4b, text="e.g. 4M — leave empty to omit", foreground="gray").grid(row=0, column=2, sticky=tk.W)

        row4c = ttk.Frame(opts)
        row4c.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row4c, text="Extra iperf3 args:").grid(row=0, column=0, sticky=tk.NW)
        ttk.Entry(row4c, textvariable=self.extra_args_var, width=70).grid(row=0, column=1, sticky=tk.EW, padx=(4, 0))
        row4c.columnconfigure(1, weight=1)
        ttk.Label(
            row4c,
            text="Appended as on CLI (quoted groups OK). Example: -O 3 --get-server-output",
            foreground="gray",
        ).grid(row=1, column=1, sticky=tk.W, padx=(4, 0))

        row5 = ttk.Frame(opts)
        row5.pack(fill=tk.X, padx=8, pady=4)
        ttk.Checkbutton(
            row5,
            text="If server says busy, try other ports (recommended for public hosts)",
            variable=self.retry_busy_var,
        ).pack(anchor=tk.W)

        self._manual_frame = ttk.LabelFrame(
            self._body_middle,
            text="Manual — arguments passed to iperf3 (program path above is used; do not repeat iperf3 here)",
        )
        ttk.Label(
            self._manual_frame,
            text="Paste anything you would type after iperf3.exe on a command prompt. "
            "A leading iperf3 / path is removed if you paste a full line.",
            wraplength=820,
        ).pack(anchor=tk.W, padx=8, pady=(4, 0))
        self.manual_cmd = scrolledtext.ScrolledText(self._manual_frame, height=6, wrap=tk.WORD, font=("Consolas", 10))
        self.manual_cmd.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.manual_cmd.insert(tk.END, "-c ping.online.net -p 5201 -t 10 -R")

        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, **pad)
        self.run_btn = ttk.Button(btn_row, text="Run test", command=self._run)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(btn_row, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Clear output", command=self._clear_output).pack(side=tk.RIGHT)

        out_frame = ttk.LabelFrame(self, text="Results")
        out_frame.pack(fill=tk.BOTH, expand=True, **pad)
        self.output = scrolledtext.ScrolledText(out_frame, height=14, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._log(f"{self._exe_status_var.get()}\n\n")
        self._log(
            "Choose a region and server preset (or Manual mode for raw iperf3 flags), then Run. "
            "Help menu: full iperf3 --help, uninstall (Apps settings), remove local iperf3.exe.\n"
            "Public servers are shared: keep tests short.\n"
            "If you see 'server is busy', leave 'try other ports' on.\n\n"
        )

    def _apply_server_preset(self) -> None:
        label = self.server_preset_var.get()
        if label == CUSTOM_SERVER_LABEL:
            return
        presets = REGION_PRESETS.get(self.region_var.get(), EU_SERVER_PRESETS)
        for p in presets:
            if p.title == label:
                self.host_var.set(p.host)
                self.port_var.set(p.port)
                extra = f" {p.note}" if p.note else ""
                self.hint_var.set(f"Server set to {p.host}:{p.port}.{extra}")
                return

    def _apply_test_preset_from_ui(self) -> None:
        self._apply_test_preset_by_title(self.test_preset_var.get(), force=False)

    def _apply_test_preset_by_title(self, title: str, force: bool) -> None:
        for p in TEST_PRESETS:
            if p.title != title:
                continue
            self.hint_var.set(p.hint)
            if p.seconds == "" and not force:
                # "Custom — keep my settings"
                return
            if p.seconds:
                self.time_var.set(p.seconds)
            if p.parallel:
                self.parallel_var.set(p.parallel)
            self.udp_var.set(p.udp)
            self.reverse_var.set(p.reverse)
            if p.bandwidth:
                self.bandwidth_var.set(p.bandwidth)
            self.ipv6_var.set(p.ipv6)
            self.json_var.set(p.json_out)
            self.bidir_var.set(p.bidir)
            self.interval_var.set(p.interval)
            self.tcp_nodelay_var.set(p.tcp_nodelay)
            return

    def _browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            title="Select iperf3.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.exe_var.set(path)
            if _verify_iperf3_cli(path):
                self._iperf3_ready = True
                self._exe_status_var.set(f"Ready — using {path}")
            else:
                self._iperf3_ready = False
                self._exe_status_var.set("That file did not respond like iperf3 — try another executable.")

    def _clear_output(self) -> None:
        self.output.delete("1.0", tk.END)

    def _log(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)

    def _client_ports_to_try(self) -> list[str]:
        """Ports to attempt when the public server returns 'busy' (one client per port)."""
        primary = self.port_var.get().strip() or "5201"
        try:
            p0 = int(primary)
        except ValueError:
            return [primary]

        if not self.retry_busy_var.get():
            return [str(p0)]

        host = self.host_var.get().strip()
        for ep in _iter_all_server_presets():
            if ep.host == host and ep.port_retry_low is not None and ep.port_retry_high is not None:
                r = list(range(ep.port_retry_low, ep.port_retry_high + 1))
                r.sort(key=lambda x: (0 if x == p0 else 1, abs(x - p0)))
                return [str(x) for x in r]

        default = list(range(5200, 5210))
        if p0 in default:
            ordered = [p0] + [x for x in default if x != p0]
        else:
            ordered = [p0] + default
        return [str(x) for x in ordered]

    def _build_args(self, *, client_port: str | None = None) -> list[str]:
        exe = self.exe_var.get().strip()
        if not exe:
            raise ValueError("Set the path to iperf3.exe (or iperf3 on PATH).")

        if client_port is not None:
            port = client_port.strip() or "5201"
        else:
            port = self.port_var.get().strip() or "5201"
        args: list[str] = [exe]
        if self.ipv6_var.get():
            args.append("-6")

        if self.mode_var.get() == "server":
            args.extend(["-s"])
            bind = self.bind_var.get().strip()
            if bind:
                args.extend(["-B", bind])
        else:
            host = self.host_var.get().strip()
            if not host:
                raise ValueError("Enter a server address, or choose a location above.")
            args.extend(["-c", host])

        args.extend(["-p", port])

        if self.mode_var.get() == "client":
            t = self.time_var.get().strip()
            if t:
                args.extend(["-t", t])
            p = self.parallel_var.get().strip()
            if p and p != "1":
                args.extend(["-P", p])

        if self.udp_var.get():
            args.append("-u")
            b = self.bandwidth_var.get().strip()
            if b:
                args.extend(["-b", b])

        if self.json_var.get():
            args.append("-J")
        if self.tcp_nodelay_var.get():
            args.append("-N")
        if self.bidir_var.get():
            args.append("--bidir")
        elif self.reverse_var.get():
            args.append("-R")

        iv = self.interval_var.get().strip()
        if iv:
            args.extend(["-i", iv])
        w = self.window_var.get().strip()
        if w:
            args.extend(["-w", w])

        extra = self.extra_args_var.get().strip()
        if extra:
            args.extend(shlex.split(extra, posix=False))

        return args

    def _parse_manual_command(self) -> list[str]:
        if self.manual_cmd is None:
            raise ValueError("Manual command area is not ready.")
        raw = self.manual_cmd.get("1.0", tk.END).strip()
        if not raw:
            raise ValueError("Enter iperf3 arguments (for example: -c example.com -p 5201 -t 10 -R).")
        try:
            parts = shlex.split(raw, posix=False)
        except ValueError as e:
            raise ValueError(f"Could not parse arguments: {e}") from e
        if not parts:
            raise ValueError("No arguments after parsing.")
        exe_base = parts[0].replace("\\", "/").split("/")[-1].lower()
        if exe_base in ("iperf3.exe", "iperf3"):
            parts = parts[1:]
            if not parts:
                raise ValueError("Only the program name was found; add flags such as -c or -s.")
        exe = self.exe_var.get().strip()
        if not exe:
            raise ValueError("Set the iperf3 program path above.")
        return [exe] + parts

    def _manual_command_worker(self) -> None:
        last_code = 2
        try:
            try:
                args = self._parse_manual_command()
            except ValueError as e:
                self._out_queue.put(f"\n{e}\n")
            else:
                self._out_queue.put(f"\n--- Command: {' '.join(args)}\n")
                try:
                    proc = subprocess.Popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        bufsize=1,
                        creationflags=_no_window_flags(),
                    )
                except OSError as e:
                    self._out_queue.put(f"Failed to start: {e}\n")
                else:
                    self._proc = proc
                    chunks: list[str] = []
                    try:
                        assert proc.stdout
                        for line in proc.stdout:
                            chunks.append(line)
                            self._out_queue.put(line)
                            if self._run_cancel.is_set():
                                proc.terminate()
                                break
                    finally:
                        rc = proc.wait() if proc.poll() is None else (proc.returncode or 0)
                        self._proc = None
                        last_code = rc
        finally:
            self._out_queue.put(f"\n--- Finished (exit code {last_code}) ---\n")
            self._out_queue.put(None)

    def _run(self) -> None:
        if (self._proc is not None and self._proc.poll() is None) or (
            self._client_worker is not None and self._client_worker.is_alive()
        ):
            messagebox.showinfo("Busy", "A test is already running. Stop it first.")
            return

        if self.command_mode_var.get() == "manual":
            exe = self.exe_var.get().strip()
            if not exe:
                messagebox.showerror("Check settings", "Set the path to iperf3.exe (or iperf3 on PATH).")
                return
            exe_path = exe
            if not os.path.isfile(exe_path) and os.path.dirname(exe_path) == "":
                pass
            elif not os.path.isfile(exe_path):
                messagebox.showerror(
                    "iperf3 not found",
                    f"File does not exist:\n{exe_path}\n\nUse Fetch iperf3, Browse, or add iperf3 to PATH.",
                )
                return
            verify_target = exe_path if os.path.isfile(exe_path) else (shutil.which(exe_path) or "")
            if verify_target and os.path.isfile(verify_target) and not _verify_iperf3_cli(verify_target):
                if not messagebox.askyesno(
                    "Not verified",
                    "This executable did not pass a quick iperf3 --version check.\nRun anyway?",
                ):
                    return
            try:
                self._parse_manual_command()
            except ValueError as e:
                messagebox.showerror("Manual command", str(e))
                return
            self._run_cancel.clear()
            self.run_btn.configure(state=tk.DISABLED)
            self.stop_btn.configure(state=tk.NORMAL)
            self._client_worker = threading.Thread(target=self._manual_command_worker, daemon=True)
            self._client_worker.start()
            self.after(200, self._watch_client_worker)
            return

        try:
            probe_args = self._build_args()
        except ValueError as e:
            messagebox.showerror("Check settings", str(e))
            return

        exe_path = probe_args[0]
        if not os.path.isfile(exe_path) and os.path.dirname(exe_path) == "":
            pass
        elif not os.path.isfile(exe_path):
            messagebox.showerror(
                "iperf3 not found",
                f"File does not exist:\n{exe_path}\n\nUse Fetch iperf3, Browse, or add iperf3 to PATH.",
            )
            return

        verify_target = exe_path if os.path.isfile(exe_path) else (shutil.which(exe_path) or "")
        if verify_target and os.path.isfile(verify_target) and not _verify_iperf3_cli(verify_target):
            if not messagebox.askyesno(
                "Not verified",
                "This executable did not pass a quick iperf3 --version check.\nRun anyway?",
            ):
                return

        if self.mode_var.get() == "client":
            self._run_cancel.clear()
            self.run_btn.configure(state=tk.DISABLED)
            self.stop_btn.configure(state=tk.NORMAL)
            self._client_worker = threading.Thread(target=self._client_run_worker, daemon=True)
            self._client_worker.start()
            self.after(200, self._watch_client_worker)
            return

        args = probe_args
        self._log(f"\n--- Command: {' '.join(args)}\n")

        try:
            self._proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=_no_window_flags(),
            )
        except OSError as e:
            messagebox.showerror("Failed to start", str(e))
            self._proc = None
            return

        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

        def reader() -> None:
            assert self._proc and self._proc.stdout
            try:
                for line in self._proc.stdout:
                    self._out_queue.put(line)
            except Exception:
                pass
            self._out_queue.put(None)

        self._reader_thread = threading.Thread(target=reader, daemon=True)
        self._reader_thread.start()
        self.after(200, self._watch_process)

    def _client_run_worker(self) -> None:
        ports = self._client_ports_to_try()
        last_code = 1
        try:
            for i, port in enumerate(ports):
                if self._run_cancel.is_set():
                    self._out_queue.put("\n--- Cancelled ---\n")
                    break
                try:
                    args = self._build_args(client_port=port)
                except ValueError:
                    break
                self._out_queue.put(f"\n--- Command: {' '.join(args)}\n")
                try:
                    proc = subprocess.Popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        bufsize=1,
                        creationflags=_no_window_flags(),
                    )
                except OSError as e:
                    self._out_queue.put(f"Failed to start: {e}\n")
                    break
                self._proc = proc
                chunks: list[str] = []
                try:
                    assert proc.stdout
                    for line in proc.stdout:
                        chunks.append(line)
                        self._out_queue.put(line)
                        if self._run_cancel.is_set():
                            proc.terminate()
                            break
                finally:
                    rc = proc.wait() if proc.poll() is None else (proc.returncode or 0)
                    self._proc = None
                full = "".join(chunks)
                last_code = rc
                if last_code == 0:
                    break
                low = full.lower()
                busy = "server is busy" in low or "busy running a test" in low
                if busy and i < len(ports) - 1 and not self._run_cancel.is_set():
                    self._out_queue.put("\n(Server busy on this port — trying another port…)\n")
                    continue
                break
        finally:
            self._out_queue.put(f"\n--- Finished (exit code {last_code}) ---\n")
            self._out_queue.put(None)

    def _watch_client_worker(self) -> None:
        if self._client_worker is not None and self._client_worker.is_alive():
            self.after(200, self._watch_client_worker)
            return
        self._client_worker = None
        self.run_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _drain_output_queue(self) -> None:
        try:
            while True:
                chunk = self._out_queue.get_nowait()
                if chunk is None:
                    break
                self._log(chunk)
        except queue.Empty:
            pass
        self.after(100, self._drain_output_queue)

    def _watch_process(self) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is not None:
            code = self._proc.returncode
            self._log(f"\n--- Finished (exit code {code})\n")
            self._proc = None
            self.run_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)
        else:
            self.after(200, self._watch_process)

    def _stop(self) -> None:
        self._run_cancel.set()
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass
            self._log("\n--- Stop requested ---\n")


def main() -> None:
    app = Iperf3GUI()
    app.mainloop()


if __name__ == "__main__":
    main()
