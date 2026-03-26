# Build portable EXE (PyInstaller) and MSI (cx_Freeze). Run from this folder.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Remove previous EXE / MSI from dist ===" -ForegroundColor Yellow
$dist = Join-Path $PSScriptRoot "dist"
if (-not (Test-Path $dist)) { New-Item -ItemType Directory -Path $dist | Out-Null }
# Old MSIs always removed. EXE may be in use; stale files cleared when possible.
Get-ChildItem -Path $dist -Filter "*.msi" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $dist -Filter "iperf3-gui-new.exe" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $dist -Filter "iperf3-gui.exe" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "dist_build") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "build_pyinstaller") -ErrorAction SilentlyContinue

python -m pip install --upgrade pip
python -m pip install "pyinstaller>=6.0" "cx_Freeze>=7.0"

Write-Host "=== PyInstaller: single-file EXE ===" -ForegroundColor Cyan
# Build as iperf3-gui-new.exe first so a running iperf3-gui.exe does not block the build.
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "iperf3-gui-new" `
    --onefile `
    --distpath $dist `
    "iperf3_gui.py"

$newExe = Join-Path $dist "iperf3-gui-new.exe"
$finalExe = Join-Path $dist "iperf3-gui.exe"
if (Test-Path $newExe) {
    if (Test-Path $finalExe) {
        try {
            Remove-Item -LiteralPath $finalExe -Force
        } catch {
            Write-Warning "Could not remove old iperf3-gui.exe (close the app if it is running). Using: $newExe"
        }
    }
    if (-not (Test-Path $finalExe)) {
        Move-Item -LiteralPath $newExe -Destination $finalExe -Force
    }
}

Write-Host "=== cx_Freeze: MSI installer ===" -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
python freeze_setup.py bdist_msi

Write-Host ""
Write-Host "Done." -ForegroundColor Green
$msi = Get-ChildItem -Path $dist -Filter "*.msi" -File -ErrorAction SilentlyContinue | Select-Object -First 1
Write-Host "  EXE: $dist\iperf3-gui.exe"
if ($msi) { Write-Host "  MSI: $($msi.FullName)" }
