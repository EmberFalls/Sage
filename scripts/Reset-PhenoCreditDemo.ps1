param([int]$ApiPort = 8000)
$ErrorActionPreference = 'Stop'
$response = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$ApiPort/api/demo/seed" -TimeoutSec 10
if ($response.status -ne 'seeded' -or $response.borrower_count -ne 2) {
    throw 'Seed endpoint did not return the expected two synthetic demo borrowers.'
}
Write-Host "Seeded $($response.borrower_count) demo borrowers from source version $($response.source_version)."
