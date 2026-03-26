# Releasing

1. **Bump version** in both places (keep them equal):
   - `iperf3_gui.py` → `__version__`
   - `freeze_setup.py` → `version=` in `setup(...)`
2. **Changelog** — add a section under `CHANGELOG.md` with the new version and date.
3. **Commit** on `main` (or your release branch):

   ```text
   git add -A
   git status   # confirm dist/, build/, *.spec are not listed
   git commit -m "Release vX.Y.Z"
   ```

4. **Tag** (annotated tag is typical):

   ```text
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

5. **Build Windows binaries** (local Windows):

   ```powershell
   .\build_release.ps1
   ```

6. **Linux**
   - **GitHub Actions:** push the tag; workflow **Build Linux binary and .deb** uploads **`iperf3-gui-linux-vX.Y.Z`** containing the raw binary and **`iperf3-gui_X.Y.Z_amd64.deb`**.
   - **Local Linux:** `./build_linux.sh` for **`dist/iperf3-gui`**, or `./build_deb.sh` for binary + **`dist/iperf3-gui_X.Y.Z_amd64.deb`**.

7. **Publish** (common pattern):
   - `git push origin main` and `git push origin vX.Y.Z`
   - **GitHub → Releases → New release**, tag `vX.Y.Z`, notes from `CHANGELOG.md`, attach:
     - `dist\iperf3-gui.exe`
     - `dist\iperf3-gui-*-win64.msi`
     - From the Linux CI artifact: **`iperf3-gui`** and **`iperf3-gui_*_amd64.deb`**

Do **not** commit secrets. Do **not** commit `dist/`, `build/`, or `*.spec`.
