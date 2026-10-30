@echo off
cd /d "%~dp0"
if exist "dist\Zhiwei\Zhiwei.exe" (
  start "" "dist\Zhiwei\Zhiwei.exe"
) else (
  start "" pythonw main.py
)
