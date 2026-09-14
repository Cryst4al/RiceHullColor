param(
    [string]$Python = "python",
    [switch]$WithoutTiffExtras
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

& $Python -m venv $VenvPath
& $PythonExe -m pip install --upgrade pip
if ($WithoutTiffExtras) {
    & $PythonExe -m pip install -e $ProjectRoot
} else {
    & $PythonExe -m pip install -e "$ProjectRoot[tiff]"
}

Write-Host "RiceHullColor installation completed." -ForegroundColor Green
Write-Host "Start the GUI with: $ProjectRoot\run_gui.cmd"

