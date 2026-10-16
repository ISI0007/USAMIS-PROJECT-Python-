# Runs psql against the USAMIS dev database, reading credentials from .env.
# Usage: .\_psql_run.ps1 -Sql "\dt"
param([string]$Sql = "\dt")
$ErrorActionPreference = "Stop"
$root = "C:\Users\Admin\.openclaw\workspace\USAMIS-PROJECT-Python"
$url = ((Select-String -Path "$root\.env" -Pattern '^DATABASE_URL=' | Select-Object -First 1).Line -replace '^DATABASE_URL=', '').Trim()
$m = [regex]::Match($url, '://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$')
if (-not $m.Success) { Write-Error "Could not parse DATABASE_URL"; exit 1 }
$env:PGPASSWORD = $m.Groups[2].Value
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
& $psql -h $m.Groups[3].Value -p $m.Groups[4].Value -U $m.Groups[1].Value -d $m.Groups[5].Value -c $Sql
