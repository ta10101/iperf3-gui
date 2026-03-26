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

5. **Build binaries** (on a clean machine or CI if you want zero local paths in artifacts):

   ```powershell
   .\build_release.ps1
   ```

6. **Publish** (common pattern):
   - Push branch and tags: `git push origin main` and `git push origin vX.Y.Z`
   - On GitHub: **Releases → Draft a new release**, choose tag `vX.Y.Z`, paste notes from `CHANGELOG.md`, attach **`dist\iperf3-gui.exe`** and **`dist\iperf3-gui-*-win64.msi`** as release assets.

Do **not** attach or commit secrets. Do **not** commit `dist/`, `build/`, or `*.spec`.
