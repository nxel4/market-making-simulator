$ErrorActionPreference = "Stop"

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Arguments = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Arguments = @() }
    }
    throw "Python wurde nicht gefunden. Installiere Python 3.11+ von https://python.org und starte das Setup erneut."
}

$python = Find-Python
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "Erstelle isolierte Python-Umgebung ..." -ForegroundColor Cyan
& $python.Command @($python.Arguments) -m venv .venv

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
Write-Host "Installiere Abhängigkeiten ..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements-dev.txt

Write-Host "Führe Tests aus ..." -ForegroundColor Cyan
& $venvPython -m pytest

Write-Host "Setup abgeschlossen. Starte die App mit .\run_app.ps1" -ForegroundColor Green
