#!/usr/bin/env bash
# Builds a single-file Windows executable using PyInstaller (for use from Git Bash).
set -e

NAME="${1:-InfraToolbox}"

py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --noconfirm --onefile --windowed --name "$NAME" main.py

cp -f config.example.json "dist/config.json"
echo "Build complete: dist/$NAME.exe (edit dist/config.json before running)"
