$ErrorActionPreference = "Stop"
$Compose = "$PSScriptRoot\docker-compose.yaml"

function Assert-Ok($msg) { if ($LASTEXITCODE -ne 0) { Write-Error $msg; exit 1 } }

docker compose -f $Compose up -d pgvector
Assert-Ok "pgvector failed to start"

$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    docker compose -f $Compose exec -T pgvector pg_isready -U postgres 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep 2
}
if ($LASTEXITCODE -ne 0) { Write-Error "pgvector never became ready"; exit 1 }

docker compose -f $Compose exec -T pgvector bash -c "psql -U postgres -c 'CREATE DATABASE sentinelai' || true"
Assert-Ok "CREATE DATABASE failed"

python "$PSScriptRoot\database\database\tables.py"
Assert-Ok "database/tables.py failed"

docker compose -f $Compose up -d --build api
Assert-Ok "api failed to start"

$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try { if ((Invoke-WebRequest http://localhost:8006/health -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $ready = $true; break } } catch {}
    Start-Sleep 2
}
if (-not $ready) { Write-Error "API health check timed out"; docker compose -f $Compose stop api pgvector; exit 1 }

python -m pytest "$PSScriptRoot\api\tests" -v --tb=short
$exit = $LASTEXITCODE

docker compose -f $Compose stop api pgvector
exit $exit
