[CmdletBinding()]
param(
    [ValidateRange(1, 50)]
    [int]$Users = 5,
    [ValidateRange(1, 10)]
    [int]$SpawnRate = 1,
    [ValidateSet('10s', '30s', '1m', '2m', '5m')]
    [string]$RunTime = '30s'
)

$ErrorActionPreference = 'Stop'
$HostUrl = 'http://127.0.0.1:8000'

try {
    $health = Invoke-RestMethod -Uri "$HostUrl/health" -TimeoutSec 3
    if ($health.status -ne 'healthy') {
        throw 'The local API health check returned an unexpected payload.'
    }
}
catch {
    throw "Local API unavailable at $HostUrl. Start it first with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
}

New-Item -ItemType Directory -Path 'results' -Force | Out-Null
Write-Host "Running a bounded load test against $HostUrl (users=$Users, spawn-rate=$SpawnRate, runtime=$RunTime)."
python -m locust -f load_tests/locustfile.py --host $HostUrl --headless --users $Users --spawn-rate $SpawnRate --run-time $RunTime --stop-timeout 5 --csv results/performance
if ($LASTEXITCODE -ne 0) {
    throw "Locust failed with exit code $LASTEXITCODE."
}
Write-Host 'CSV results were written to the results/ prefix. Review request failures and p95/p99 before drawing conclusions.'
