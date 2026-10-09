param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backend = Join-Path $repo 'backend'
$frontend = Join-Path $repo 'frontend'
$runDir = Join-Path $repo 'demo/run'
$pidFile = Join-Path $runDir 'processes.json'
$logDir = Join-Path $runDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$inheritedApiUrl = $env:VITE_API_BASE_URL
$configuredApiUrl = $false
$envFile = Join-Path $repo '.env'
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*(PRODUCT_NAME|VITE_PRODUCT_NAME|DATABASE_URL|DEMO_SEED|VITE_API_BASE_URL)\s*=\s*(.*?)\s*$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
            if ($Matches[1] -eq 'VITE_API_BASE_URL') { $configuredApiUrl = $true }
        }
    }
}
if (-not $configuredApiUrl) {
    $apiUrl = if (-not [string]::IsNullOrWhiteSpace($inheritedApiUrl)) { $inheritedApiUrl } else { "http://127.0.0.1:$ApiPort" }
    [Environment]::SetEnvironmentVariable('VITE_API_BASE_URL', $apiUrl, 'Process')
}

function Test-HttpOk([string]$Url) {
    try { Invoke-RestMethod -Uri $Url -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}

if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/health")) {
    $python = Join-Path $backend '.venv-runtime/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $backend '.venv/Scripts/python.exe' }
    if (-not (Test-Path -LiteralPath $python)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $pythonCommand) { throw 'Python 3.10+ was not found. Create backend/.venv and install backend/requirements.txt.' }
        $python = $pythonCommand.Source
    }
    $packages = Join-Path $backend '.packages'
    if (Test-Path -LiteralPath $packages) {
        $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $packages } else { "$packages$([IO.Path]::PathSeparator)$env:PYTHONPATH" }
    }
    & $python -c 'import fastapi, uvicorn' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependencies are missing. Run: python -m pip install -r backend/requirements.txt' }
    $api = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort") `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDir 'api.log') -RedirectStandardError (Join-Path $logDir 'api-error.log')
} else { $api = $null }

if (-not (Test-HttpOk "http://127.0.0.1:$WebPort/")) {
    $vite = Join-Path $frontend 'node_modules/vite/bin/vite.js'
    if (-not (Test-Path -LiteralPath $vite)) { throw 'Frontend dependencies are missing. Run npm ci from frontend.' }
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $nodeCommand) { throw 'Node.js 20+ was not found.' }
    $web = Start-Process -FilePath $nodeCommand.Source -ArgumentList @($vite,'--host','127.0.0.1','--port',"$WebPort") `
        -WorkingDirectory $frontend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDir 'web.log') -RedirectStandardError (Join-Path $logDir 'web-error.log')
} else { $web = $null }

for ($i = 0; $i -lt 30; $i++) {
    if ((Test-HttpOk "http://127.0.0.1:$ApiPort/health") -and (Test-HttpOk "http://127.0.0.1:$WebPort/")) { break }
    Start-Sleep -Milliseconds 500
}
if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/health")) { throw "API did not start. See $logDir/api-error.log" }
if (-not (Test-HttpOk "http://127.0.0.1:$WebPort/")) { throw "Frontend did not start. See $logDir/web-error.log" }

$owned = @()
if (Test-Path -LiteralPath $pidFile) {
    try {
        foreach ($entry in @(Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json)) {
            if (Get-Process -Id $entry.Id -ErrorAction SilentlyContinue) { $owned += $entry }
        }
    } catch { $owned = @() }
}
if ($api) { $owned += [pscustomobject]@{ Id = $api.Id; Kind = 'api'; Port = $ApiPort } }
if ($web) { $owned += [pscustomobject]@{ Id = $web.Id; Kind = 'web'; Port = $WebPort } }
$owned | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
Write-Host "Sage is ready: http://127.0.0.1:$WebPort/"
Write-Host "API health: http://127.0.0.1:$ApiPort/health"
Write-Host 'Demo records are seeded automatically. Run scripts/Stop-SageDemo.ps1 when finished.'
