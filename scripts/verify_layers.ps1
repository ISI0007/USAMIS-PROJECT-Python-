param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not $env:TEST_DATABASE_URL -or $env:TEST_DATABASE_URL -notmatch '(test|codex)') {
    throw 'Set TEST_DATABASE_URL to a dedicated disposable PostgreSQL test database. Tests reset its tables.'
}
$checks = @(
    @{ Name = 'Layer 1: presentation syntax'; Files = @('tests/unit/test_layer_boundaries.py::test_layer_1_all_templates_compile_without_server') },
    @{ Name = 'Layer 2: application access and HTTP workflows'; Files = @('tests/security', 'tests/integration/test_auth_workflow.py', 'tests/integration/test_neural_and_scanner.py') },
    @{ Name = 'Layer 3: academic algorithms'; Files = @('tests/unit') },
    @{ Name = 'Layer 4: PostgreSQL persistence and constraints'; Files = @('tests/integration/test_persistence.py', 'tests/integration/test_enrollment_algorithm.py', 'tests/integration/test_fee_workflow.py') }
)
foreach ($check in $checks) {
    Write-Host $check.Name
    & $Python -m pytest @($check.Files) -q --basetemp=instance/layer-check-tmp
    if ($LASTEXITCODE -ne 0) { throw "$($check.Name) failed" }
}
Write-Host 'Each layer check passed. Run the full suite for cross-feature regression coverage.'
