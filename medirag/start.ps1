# MediRAG - Quick Start
#
# Run this script from the medirag/ directory.
# It starts both the FastAPI backend and Vite frontend.

$ErrorActionPreference = "Continue"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   MediRAG - Clinical Intelligence Oracle" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Check .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "! Copied .env.example -> .env" -ForegroundColor Yellow
        Write-Host "  Edit .env and add your DEEPSEEK_API_KEY before using the backend." -ForegroundColor Yellow
    }
}

# Start backend in a new window
Write-Host "* Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Green
$backendCmd = "Set-Location -LiteralPath '$PSScriptRoot'; pip install -r requirements.txt -q; python -m spacy download en_core_web_sm; uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $backendCmd }"

Start-Sleep -Seconds 2

# Start frontend in a new window
Write-Host "* Starting Vite frontend on http://localhost:5173 ..." -ForegroundColor Green
$frontendCmd = "Set-Location -LiteralPath '$PSScriptRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $frontendCmd }"

Start-Sleep -Seconds 3

Write-Host "`nOK MediRAG is running!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs: http://localhost:8000/docs`n" -ForegroundColor White
Write-Host "NOTE: The frontend works in demo mode without the backend." -ForegroundColor Yellow
Write-Host "      Add your DEEPSEEK_API_KEY in .env for full AI analysis.`n" -ForegroundColor Yellow
