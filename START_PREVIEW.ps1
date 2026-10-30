param([int]$Port = 5055, [string]$Python = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not $Python) {
    $candidate = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
    $Python = if (Test-Path $candidate) { $candidate } else { 'python' }
}
Write-Host "USAMIS preview: http://127.0.0.1:$Port"
& $Python -m flask --app wsgi run --host 127.0.0.1 --port $Port --no-reload --no-debugger
