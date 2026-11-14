# Preparacion en Windows. Ejecutar desde la carpeta del proyecto:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) { py -3.12 -m venv .venv 2>$null; if (-not (Test-Path .venv)) { py -3 -m venv .venv } } else { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = "."
.\.venv\Scripts\python -m pytest -q tests
.\.venv\Scripts\python -c "import control_arena, inspect_ai; print('control-arena', control_arena.__version__ if hasattr(control_arena,'__version__') else 'ok', '| python ok')"
Write-Host "Listo. Falta: copiar .env.example a .env y poner la API key."
