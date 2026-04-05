$ErrorActionPreference = "Stop"
$Compose    = "$PSScriptRoot\docker-compose.yaml"
$Network    = "sentinelai_default"
$TestImage  = "sentinelai-webhooks-test"

function Assert-Ok($msg) { if ($LASTEXITCODE -ne 0) { Write-Error $msg; exit 1 } }

# ── 1. pgvector ───────────────────────────────────────────────────
Write-Host "━━━ Starting pgvector ━━━" -ForegroundColor Cyan
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
Assert-Ok "Schema migration failed"

# Seed test plan
docker compose -f $Compose exec -T pgvector psql -U postgres -d sentinelai -c "INSERT INTO subscription_plans (plan_name, price_pennies, seat_limit) VALUES ('Test Plan', 0, 999) ON CONFLICT DO NOTHING;"
Assert-Ok "Seed test plan failed"

# ── 2. API (webhooks now calls it for all DB ops) ─────────────────
Write-Host "━━━ Starting API ━━━" -ForegroundColor Cyan
docker compose -f $Compose up -d --build api
Assert-Ok "api failed to start"

$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest http://localhost:8006/health -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep 2
}
if (-not $ready) {
    Write-Error "API health check timed out"
    docker compose -f $Compose stop api pgvector
    exit 1
}

# ── 3. Build webhook test image ───────────────────────────────────
Write-Host "━━━ Building webhook test image ━━━" -ForegroundColor Cyan
docker build -f "$PSScriptRoot\webhooks\Dockerfile.test" -t $TestImage "$PSScriptRoot"
Assert-Ok "Webhook test image build failed"

# ── 4. Run tests ──────────────────────────────────────────────────
Write-Host "━━━ Running webhook tests ━━━" -ForegroundColor Cyan
$testOutput = docker run --rm `
    --network $Network `
    -e INTERNAL_API_URL=http://api:8000 `
    $TestImage 2>&1

$exit = $LASTEXITCODE

# Parse and display results
if ($exit -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "✗ Tests failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "━━━ Issues ━━━" -ForegroundColor Yellow

    # Show only failed tests, errors, and warnings
    $lines = $testOutput -split "`n"
    $inFailure = $false
    foreach ($line in $lines) {
        if ($line -match "FAILED|ERROR|WARNING|AssertionError|Traceback" -or $inFailure) {
            if ($line -match "^=") {
                $inFailure = -not $inFailure
                if ($inFailure) {
                    Write-Host ""
                }
            }
            if ($line -match "FAILED") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "ERROR") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "WARNING") {
                Write-Host $line -ForegroundColor Yellow
            } else {
                Write-Host $line
            }
        }
    }

    Write-Host ""
    Write-Host "━━━ Summary ━━━" -ForegroundColor Yellow
    $summaryLine = $lines | Select-String "passed|failed" | Select-Object -Last 1
    if ($summaryLine) {
        Write-Host $summaryLine.Line -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "━━━ Cleanup ━━━" -ForegroundColor Cyan
docker compose -f $Compose stop api pgvector

exit $exit
