#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Pipeline script to export, quantize, and upload ONNX models to HuggingFace.

.DESCRIPTION
    This script runs the complete pipeline:
    1. Export base ONNX model from PyTorch checkpoint
    2. Generate all quantized variants (FP16, Dynamic INT8, Static INT8)
    3. Upload all models to HuggingFace

.REQUIREMENTS
    - HF_TOKEN environment variable set (HuggingFace write token)
    - Trained PyTorch model checkpoint in filter/models/
    - Python virtual environment activated

.EXAMPLE
    .\pipeline_quantize_and_upload.ps1
#>

param(
    [switch]$SkipExport,     # Skip ONNX export (if model already exported)
    [switch]$SkipQuantize,   # Skip quantization (if quantized models exist)
    [switch]$SkipUpload      # Skip upload (for testing)
)

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"

# Get script directory and filter root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FilterRoot = Split-Path -Parent $ScriptDir

Write-Host "="*80 -ForegroundColor $Cyan
Write-Host "SentinelAI ONNX Model Pipeline" -ForegroundColor $Cyan
Write-Host "Export → Quantize → Upload to HuggingFace" -ForegroundColor $Cyan
Write-Host "="*80 -ForegroundColor $Cyan
Write-Host ""

# Load .env file if exists
$EnvFile = Join-Path $FilterRoot ".env"
if (Test-Path $EnvFile) {
    Write-Host "[INFO] Loading environment from .env file..." -ForegroundColor $Cyan
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
            $key = $matches[1]
            $value = $matches[2]
            # Remove quotes if present
            $value = $value.Trim('"', "'")
            Set-Item -Path "env:$key" -Value $value
            Write-Host "  Loaded: $key" -ForegroundColor $Cyan
        }
    }
    Write-Host ""
}

# Check HF_TOKEN
if (-not $env:HF_TOKEN -and -not $SkipUpload) {
    Write-Host "[ERROR] HF_TOKEN environment variable not set!" -ForegroundColor $Red
    Write-Host "Please set your HuggingFace write token:" -ForegroundColor $Yellow
    Write-Host '  $env:HF_TOKEN = "hf_..."' -ForegroundColor $Yellow
    Write-Host "Or use -SkipUpload to skip the upload step" -ForegroundColor $Yellow
    exit 1
}

# Track pipeline status
$PipelineSuccess = $true

# ============================================================================
# STEP 1: Export Base ONNX Model
# ============================================================================
if (-not $SkipExport) {
    Write-Host ""
    Write-Host "STEP 1/3: Exporting base ONNX model..." -ForegroundColor $Cyan
    Write-Host "-"*80 -ForegroundColor $Cyan
    
    Push-Location $FilterRoot
    try {
        python scripts/export_onnx.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] ONNX export failed!" -ForegroundColor $Red
            $PipelineSuccess = $false
        } else {
            Write-Host ""
            Write-Host "[SUCCESS] Base ONNX model exported" -ForegroundColor $Green
        }
    }
    catch {
        Write-Host "[ERROR] Failed to run export_onnx.py: $_" -ForegroundColor $Red
        $PipelineSuccess = $false
    }
    finally {
        Pop-Location
    }
    
    if (-not $PipelineSuccess) {
        Write-Host ""
        Write-Host "Pipeline failed at STEP 1" -ForegroundColor $Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "STEP 1/3: Skipping ONNX export (--SkipExport)" -ForegroundColor $Yellow
}

# ============================================================================
# STEP 2: Quantize Models
# ============================================================================
if (-not $SkipQuantize) {
    Write-Host ""
    Write-Host "STEP 2/3: Generating quantized models..." -ForegroundColor $Cyan
    Write-Host "-"*80 -ForegroundColor $Cyan
    
    Push-Location $FilterRoot
    try {
        python scripts/quantize_onnx.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Quantization failed!" -ForegroundColor $Red
            $PipelineSuccess = $false
        } else {
            Write-Host ""
            Write-Host "[SUCCESS] All quantized models generated" -ForegroundColor $Green
        }
    }
    catch {
        Write-Host "[ERROR] Failed to run quantize_onnx.py: $_" -ForegroundColor $Red
        $PipelineSuccess = $false
    }
    finally {
        Pop-Location
    }
    
    if (-not $PipelineSuccess) {
        Write-Host ""
        Write-Host "Pipeline failed at STEP 2" -ForegroundColor $Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "STEP 2/3: Skipping quantization (--SkipQuantize)" -ForegroundColor $Yellow
}

# ============================================================================
# STEP 3: Upload to HuggingFace
# ============================================================================
if (-not $SkipUpload) {
    Write-Host ""
    Write-Host "STEP 3/3: Uploading models to HuggingFace..." -ForegroundColor $Cyan
    Write-Host "-"*80 -ForegroundColor $Cyan
    
    Push-Location $FilterRoot
    try {
        python scripts/upload_to_hf.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Upload failed!" -ForegroundColor $Red
            $PipelineSuccess = $false
        } else {
            Write-Host ""
            Write-Host "[SUCCESS] Models uploaded to HuggingFace" -ForegroundColor $Green
        }
    }
    catch {
        Write-Host "[ERROR] Failed to run upload_to_hf.py: $_" -ForegroundColor $Red
        $PipelineSuccess = $false
    }
    finally {
        Pop-Location
    }
    
    if (-not $PipelineSuccess) {
        Write-Host ""
        Write-Host "Pipeline failed at STEP 3" -ForegroundColor $Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "STEP 3/3: Skipping upload (--SkipUpload)" -ForegroundColor $Yellow
}

# ============================================================================
# Pipeline Complete
# ============================================================================
Write-Host ""
Write-Host "="*80 -ForegroundColor $Green
Write-Host "PIPELINE COMPLETE!" -ForegroundColor $Green
Write-Host "="*80 -ForegroundColor $Green

if (-not $SkipUpload) {
    Write-Host ""
    Write-Host "Models uploaded to HuggingFace and ready for inference!" -ForegroundColor $Green
    Write-Host "Available models:" -ForegroundColor $Cyan
    Write-Host "  - sentinelai_model.onnx (FP32 base)" -ForegroundColor $Cyan
    Write-Host "  - sentinelai_model_fp16.onnx" -ForegroundColor $Cyan
    Write-Host "  - sentinelai_model_dynamic_int8.onnx" -ForegroundColor $Cyan
    Write-Host "  - sentinelai_model_static_int8.onnx" -ForegroundColor $Cyan
}

Write-Host ""
