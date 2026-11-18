$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Die Projektumgebung fehlt. Führe zuerst .\setup.ps1 aus."
}

Set-Location $projectRoot
& $python -m streamlit run app.py
