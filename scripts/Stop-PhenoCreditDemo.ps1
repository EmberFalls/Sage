$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $repo 'demo/run/processes.json'
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host 'No demo processes were started by the launcher.'
    exit 0
}

$owned = @(Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json)
foreach ($entry in $owned) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.Id)" -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    $expected = if ($entry.Kind -eq 'api') { $process.CommandLine -match 'uvicorn.*app\.main:app' } else { $process.CommandLine -match 'vite\.js.*--host 127\.0\.0\.1' }
    if ($expected) { Stop-Process -Id $entry.Id -Force -ErrorAction SilentlyContinue }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Host 'Stopped PhenoCredit processes started by the launcher.'
