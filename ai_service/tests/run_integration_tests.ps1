# SentinelAI Integration Test Runner
# Runs integration tests against deployed Docker containers

Write-Host "================================" -ForegroundColor Cyan
Write-Host "SentinelAI Integration Tests" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Save original directory
$originalDir = Get-Location

# Navigate to ai_service directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$aiServicePath = Split-Path -Parent $scriptPath
Set-Location $aiServicePath

Write-Host "Working directory: $aiServicePath" -ForegroundColor Gray
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment not detected. Activating..." -ForegroundColor Yellow
    $venvPath = Join-Path (Split-Path -Parent $aiServicePath) ".venv"
    if (Test-Path "$venvPath\Scripts\Activate.ps1") {
        & "$venvPath\Scripts\Activate.ps1"
        Write-Host "✓ Virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "✗ Virtual environment not found at $venvPath" -ForegroundColor Red
        Write-Host "Please create virtual environment or activate it manually" -ForegroundColor Yellow
        exit 1
    }
    Write-Host ""
}

# Check if pytest is installed
Write-Host "Checking dependencies..." -ForegroundColor Gray
python -m pytest --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  pytest not found. Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✓ pytest found" -ForegroundColor Green
}
Write-Host ""

# Check if Docker containers are running
Write-Host "Checking Docker service..." -ForegroundColor Gray
$response = $null
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host "✓ AI service is running on port 8002" -ForegroundColor Green
} catch {
    Write-Host "✗ AI service not responding on port 8002" -ForegroundColor Red
    Write-Host "Please start Docker containers with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Run integration tests
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Running Integration Tests..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

python -m pytest tests/test_integration.py -v --tb=short

# Show results location
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$resultsDir = Join-Path $aiServicePath "tests\test_results"
if (Test-Path $resultsDir) {
    $latestLog = Get-ChildItem $resultsDir -Filter "integration_test_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $summaryFile = Join-Path $resultsDir "latest_test_summary.txt"
    
    if (Test-Path $summaryFile) {
        Write-Host "📄 Summary:" -ForegroundColor White
        Get-Content $summaryFile
    }
    
    if ($latestLog) {
        Write-Host ""
        Write-Host "📋 Full log: tests\test_results\$($latestLog.Name)" -ForegroundColor Gray
        Write-Host "   View with: cat tests\test_results\$($latestLog.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  Test results directory not found" -ForegroundColor Yellow
}

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "✗ Some tests failed. Check logs above." -ForegroundColor Red
}

# Restore original directory
Set-Location $originalDir

exit $LASTEXITCODE
