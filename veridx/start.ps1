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

# Function to test if a port is in use
function Test-PortInUse($Port) {
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        return ($null -ne $conn)
    } else {
        $netstat = netstat -ano | Select-String ":$Port\s+"
        return ($null -ne $netstat)
    }
}

# Check if services are already running
$backendPort = 8000
$frontendPort = 5173

$backendAlreadyRunning = Test-PortInUse $backendPort
$frontendAlreadyRunning = Test-PortInUse $frontendPort

if ($backendAlreadyRunning) {
    Write-Host "* Port $backendPort is busy. Checking if backend is already active..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$backendPort/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "ok" -or $response.status -match "ok") {
            Write-Host "* Backend is already active and healthy on http://localhost:$backendPort." -ForegroundColor Green
        } else {
            Write-Host "! Port $backendPort is in use by another process. Backend startup might fail." -ForegroundColor Red
            $backendAlreadyRunning = $false
        }
    } catch {
        Write-Host "! Could not reach VeriDX health check on port $backendPort (still starting up or another process). Will try to start backend..." -ForegroundColor Yellow
        $backendAlreadyRunning = $false
    }
}

if ($frontendAlreadyRunning) {
    Write-Host "* Vite frontend is already active on http://localhost:$frontendPort." -ForegroundColor Green
}

# Resolve the python executable path
$pythonCmd = "python"
$condaEnvPath = ""

# 1. Try to find conda env path from settings.json if it exists
$settingsPath = "$PSScriptRoot\..\.vscode\settings.json"
if (Test-Path $settingsPath) {
    try {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
        if ($settings."python.defaultInterpreterPath") {
            $candidate = $settings."python.defaultInterpreterPath"
            if (Test-Path $candidate) {
                $condaEnvPath = Split-Path $candidate -Parent
            }
        }
    } catch {}
}

# 2. If not found, try to query conda command
if (-not $condaEnvPath -and (Get-Command conda -ErrorAction SilentlyContinue)) {
    $envs = conda env list | Out-String
    if ($envs -match "(?m)^medirag\s+(\S+)") {
        $condaEnvPath = $Matches[1].Trim()
    }
}

# 3. If still not found, check common directories on Windows
if (-not $condaEnvPath) {
    $commonDirs = @(
        "$home\anaconda3\envs\medirag",
        "$home\miniconda3\envs\medirag",
        "C:\Users\SA IT SOLUTIONS\anaconda3\envs\medirag",
        "C:\ProgramData\anaconda3\envs\medirag",
        "C:\anaconda3\envs\medirag"
    )
    foreach ($dir in $commonDirs) {
        if (Test-Path $dir) {
            $condaEnvPath = $dir
            break
        }
    }
}

if ($condaEnvPath) {
    $pythonCmd = Join-Path $condaEnvPath "python.exe"
    Write-Host "* Conda environment 'medirag' detected at: $pythonCmd" -ForegroundColor Cyan
} else {
    Write-Host "* No 'medirag' Conda environment path resolved. Falling back to system 'python'..." -ForegroundColor Yellow
}

# Fast setup validation (check if packages and spaCy model are already installed)
$setupNeeded = $true
if ($backendAlreadyRunning) {
    $setupNeeded = $false
} else {
    Write-Host "* Checking backend dependencies..." -ForegroundColor Cyan
    try {
        $null = & { & "$pythonCmd" -c "import fastapi, uvicorn, chromadb, spacy; spacy.load('en_core_web_sm')" } 2>$null
        if ($LASTEXITCODE -eq 0) {
            $setupNeeded = $false
            Write-Host "* All backend dependencies and NLP models are verified." -ForegroundColor Green
        }
    } catch {
        # Ignore and do setup
    }
}

# Start backend if not already running
if (-not $backendAlreadyRunning) {
    $setupCmd = ""
    if ($setupNeeded) {
        Write-Host "* Dependencies or spaCy model missing. Running setup (requires internet)..." -ForegroundColor Yellow
        $setupCmd = "& '$pythonCmd' -m pip install -r requirements.txt; & '$pythonCmd' -m spacy download en_core_web_sm; "
    } else {
        Write-Host "* Skipping dependency installation (offline-ready startup)." -ForegroundColor Green
    }
    
    Write-Host "* Starting FastAPI backend on http://localhost:$backendPort ..." -ForegroundColor Green
    $backendCmd = "Set-Location -LiteralPath '$PSScriptRoot'; $setupCmd & '$pythonCmd' -m uvicorn backend.main:app --host 0.0.0.0 --port $backendPort --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $backendCmd }"
    
    # Wait and verify backend health (up to 40 seconds — first launch loads spaCy/Presidio/Transformers)
    Write-Host "* Verifying backend startup (may take up to 40s on first launch)..." -ForegroundColor Cyan
    $backendVerified = $false
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:$backendPort/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok" -or $response.status -match "ok") {
                $backendVerified = $true
                break
            }
        } catch {
            # Still starting — wait more
        }
    }
    if ($backendVerified) {
        Write-Host "* Backend verified successfully!" -ForegroundColor Green
    } else {
        Write-Warning "Backend is taking a while. It may still be loading NLP models in the background. Check the backend console window if it doesn't respond shortly."
    }
}

# Start frontend if not already running
if (-not $frontendAlreadyRunning) {
    Write-Host "* Starting Vite frontend on http://localhost:$frontendPort ..." -ForegroundColor Green
    $frontendCmd = "Set-Location -LiteralPath '$PSScriptRoot\frontend'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $frontendCmd }"
}

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
Write-Host "   Frontend: http://localhost:$frontendPort" -ForegroundColor White
Write-Host "   Backend:  http://localhost:$backendPort" -ForegroundColor White
Write-Host "   API Docs: http://localhost:$backendPort/docs`n" -ForegroundColor White

if ($hasDeepSeekKey) {
    Write-Host "NOTE: DeepSeek API key detected. Full clinical AI analysis is enabled.`n" -ForegroundColor Green
} else {
    Write-Host "NOTE: The frontend works in demo mode without the backend." -ForegroundColor Yellow
    Write-Host "      Add your DEEPSEEK_API_KEY in .env for full AI analysis.`n" -ForegroundColor Yellow
}
