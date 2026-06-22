param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'

Write-Host '== YT Strategy Agent Windows bootstrap =='

function Ensure-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "$name not found. $hint"
    }
}

Ensure-Command py 'Install Python 3.11+ from python.org and ensure the py launcher is available.'
Ensure-Command git 'Install Git for Windows.'

Set-Location $RepoRoot

if (-not (Test-Path .venv)) {
    py -3 -m venv .venv
}

$python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$pip = Join-Path $RepoRoot '.venv\Scripts\pip.exe'

& $python -m pip install --upgrade pip
& $pip install -r requirements.txt

if (-not (Test-Path .env) -and (Test-Path .env.example)) {
    Copy-Item .env.example .env
    Write-Host 'Created .env from .env.example'
}

$runtime = Join-Path $RepoRoot 'runtime'
$null = New-Item -ItemType Directory -Force -Path $runtime, (Join-Path $runtime 'channels'), (Join-Path $runtime 'logs')

Write-Host ''
Write-Host 'Bootstrap complete.'
Write-Host "Next steps:"
Write-Host "  1. Fill in $RepoRoot\.env"
Write-Host "  2. Put client_secret.json in the repo root or set YT_CLIENT_SECRET"
Write-Host "  3. Run: $python auth.py"
Write-Host "  4. Run: $python ingest.py --once"
Write-Host "  5. Optional background task: scripts\register_windows_task.ps1"
