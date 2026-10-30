$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m PyInstaller --noconfirm --windowed --name Zhiwei --add-data 'assets;assets' --add-data 'licenses;licenses' --hidden-import keyring.backends.Windows --exclude-module PyQt5 --exclude-module PyQt6 main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
