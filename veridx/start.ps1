# VeriDX - Quick Start
#
# Run this script from the veridx/ directory.
# It starts both the FastAPI backend and Vite frontend.

$ErrorActionPreference = "Continue"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   VeriDX - Clinical Intelligence Oracle" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Check .env
$envPath = "$PSScriptRoot\.env"
$envExamplePath = "$PSScriptRoot\.env.example"
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
        Write-Host "! Copied .env.example -> .env" -ForegroundColor Yellow
        Write-Host "  Edit .env and add your DEEPSEEK_API_KEY before using the backend." -ForegroundColor Yellow
    }
}

# Detect if a conda environment named 'medirag' exists
$condaPrefix = ""
if (Get-Command conda -ErrorAction SilentlyContinue) {
    $envs = conda env list | Out-String
    if ($envs -match "medirag\s+") {
        Write-Host "* Conda environment 'medirag' detected. Using it for the backend..." -ForegroundColor Cyan
        $condaPrefix = "conda run --no-capture-output -n medirag "
    }
}

# Start backend in a new window
Write-Host "* Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Green
$backendCmd = "Set-Location -LiteralPath '$PSScriptRoot'; ${condaPrefix}pip install -r requirements.txt -q; ${condaPrefix}python -m spacy download en_core_web_sm; ${condaPrefix}uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $backendCmd }"

Start-Sleep -Seconds 2

# Start frontend in a new window
Write-Host "* Starting Vite frontend on http://localhost:5173 ..." -ForegroundColor Green
$frontendCmd = "Set-Location -LiteralPath '$PSScriptRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $frontendCmd }"

Start-Sleep -Seconds 3

# Check if DEEPSEEK_API_KEY is configured in .env
$hasDeepSeekKey = $false
if (Test-Path $envPath) {
    $envLines = Get-Content $envPath
    foreach ($line in $envLines) {
        if ($line -match "^\s*DEEPSEEK_API_KEY\s*=\s*(.+)$") {
            $keyVal = $Matches[1].Trim()
            if ($keyVal -and $keyVal -ne "your_deepseek_api_key_here") {
                $hasDeepSeekKey = $true
                break
            }
        }
    }
}

Write-Host "`nOK VeriDX is running!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs: http://localhost:8000/docs`n" -ForegroundColor White

if ($hasDeepSeekKey) {
    Write-Host "NOTE: DeepSeek API key detected. Full clinical AI analysis is enabled.`n" -ForegroundColor Green
} else {
    Write-Host "NOTE: The frontend works in demo mode without the backend." -ForegroundColor Yellow
    Write-Host "      Add your DEEPSEEK_API_KEY in .env for full AI analysis.`n" -ForegroundColor Yellow
}
