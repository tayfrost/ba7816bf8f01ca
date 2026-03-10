#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run all inference tests for SentinelAI filter service.

.DESCRIPTION
    This script runs all inference-related tests in the inference_tests folder.
    Assumes the gRPC server is already running (e.g., via Docker container).

.PARAMETER Verbose
    Show detailed test output

.PARAMETER StopOnFailure
    Stop running tests after first failure

.PARAMETER TestFile
    Run a specific test file only (optional)

.EXAMPLE
    .\run_inference_tests.ps1
    
.EXAMPLE
    .\run_inference_tests.ps1 -Verbose
    
.EXAMPLE
    .\run_inference_tests.ps1 -TestFile test_grpc_server.py
#>

param(
    [switch]$Verbose,
    [switch]$StopOnFailure,
    [string]$TestFile
)

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"

# Get script directory
$InferenceTestsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FilterRoot = Split-Path -Parent $InferenceTestsDir
$ProjectRoot = Split-Path -Parent $FilterRoot

Write-Host ("=" * 80) -ForegroundColor $Cyan
Write-Host "SentinelAI Inference Test Suite" -ForegroundColor $Cyan
Write-Host ("=" * 80) -ForegroundColor $Cyan
Write-Host ""

# Check if we're in the right directory
if (Test-Path (Join-Path $InferenceTestsDir "test_grpc_server.py")) {
    Write-Host "[OK] Found inference tests directory" -ForegroundColor $Green
} else {
    Write-Host "[ERROR] Cannot find inference tests. Run from filter/inference_tests/ directory" -ForegroundColor $Red
    exit 1
}

# Compile protos first
Write-Host "[INFO] Compiling proto files..." -ForegroundColor $Cyan
Push-Location $FilterRoot
try {
    python scripts/compile_protos.py 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Proto files compiled" -ForegroundColor $Green
    } else {
        Write-Host "[WARNING] Proto compilation may have issues" -ForegroundColor $Yellow
    }
} catch {
    Write-Host "[WARNING] Could not compile protos: $_" -ForegroundColor $Yellow
} finally {
    Pop-Location
}

# Check if server is running
Write-Host "[INFO] Checking if gRPC server is available on localhost:50051..." -ForegroundColor $Cyan
$serverRunning = $false
try {
    $tcpTest = Test-NetConnection -ComputerName localhost -Port 50051 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($tcpTest) {
        $serverRunning = $true
        Write-Host "[OK] gRPC server is running" -ForegroundColor $Green
    }
} catch {
    Write-Host "[WARNING] Cannot check server status (this is ok if server is in Docker)" -ForegroundColor $Yellow
    $serverRunning = $true  # Assume it's running
}

if (-not $serverRunning) {
    Write-Host "[WARNING] gRPC server may not be running on localhost:50051" -ForegroundColor $Yellow
    Write-Host "          Some tests may fail if server is not started" -ForegroundColor $Yellow
    Write-Host "          Start server with: python filter/inference/server.py" -ForegroundColor $Yellow
    Write-Host ""
    
    $response = Read-Host "Continue anyway? (y/n)"
    if ($response -ne "y") {
        exit 0
    }
}

Write-Host ""

# Build pytest command
$pytestArgs = @()

if ($TestFile) {
    # Run specific test file
    $testPath = Join-Path $InferenceTestsDir $TestFile
    if (-not (Test-Path $testPath)) {
        Write-Host "[ERROR] Test file not found: $TestFile" -ForegroundColor $Red
        exit 1
    }
    $pytestArgs += $testPath
    Write-Host "[INFO] Running specific test: $TestFile" -ForegroundColor $Cyan
} else {
    # Run all tests in directory
    $pytestArgs += $InferenceTestsDir
    Write-Host "[INFO] Running all inference tests" -ForegroundColor $Cyan
}

# Add verbosity
if ($Verbose) {
    $pytestArgs += "-v"
    $pytestArgs += "-s"  # Don't capture output
} else {
    $pytestArgs += "-v"
}

# Add stop on failure
if ($StopOnFailure) {
    $pytestArgs += "-x"
}

# Add color output
$pytestArgs += "--color=yes"

# Add test capture settings
$pytestArgs += "--tb=short"  # Shorter traceback format

Write-Host ""
Write-Host "Running: pytest $($pytestArgs -join ' ')" -ForegroundColor $Cyan
Write-Host ("-" * 80) -ForegroundColor $Cyan
Write-Host ""

# Set PYTHONPATH to include project root for generated protos
$env:PYTHONPATH = "$ProjectRoot;$FilterRoot;$env:PYTHONPATH"

# Change to filter directory for proper imports
Push-Location $FilterRoot

try {
    # Run pytest
    & pytest @pytestArgs
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Cyan
    
    if ($exitCode -eq 0) {
        Write-Host "ALL TESTS PASSED ✓" -ForegroundColor $Green
        Write-Host ("=" * 80) -ForegroundColor $Green
    } elseif ($exitCode -eq 5) {
        Write-Host "NO TESTS COLLECTED" -ForegroundColor $Yellow
        Write-Host ("=" * 80) -ForegroundColor $Yellow
    } else {
        Write-Host "SOME TESTS FAILED ✗" -ForegroundColor $Red
        Write-Host ("=" * 80) -ForegroundColor $Red
    }
    
    exit $exitCode
    
} catch {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Red
    Write-Host "ERROR RUNNING TESTS" -ForegroundColor $Red
    Write-Host ("=" * 80) -ForegroundColor $Red
    Write-Host $_.Exception.Message -ForegroundColor $Red
    exit 1
} finally {
    Pop-Location
}
