# Builds a single-file Windows executable using PyInstaller.
param(
    [string]$Name = "InfraToolbox"
)

py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --noconfirm --onefile --windowed --name $Name main.py

Copy-Item config.example.json "dist\config.json" -Force
Write-Host "Build complete: dist\$Name.exe (edit dist\config.json before running)"
