Set-Location $PSScriptRoot

Write-Host "========================================="
Write-Host " Configuring Agentica Dependencies...    "
Write-Host "========================================="

# 1. Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "CRITICAL ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "Agentica requires Python. Please install Python from python.org or the Microsoft Store."
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# 2. Create an isolated Python environment (venv)
Write-Host "Creating isolated Python environment..."
python -m venv venv

# 3. Install Requirements
Write-Host "Installing required libraries (skips if already installed)..."
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Install Chromium via Playwright
# Playwright uses smart caching: it will skip the download if Chromium is already present globally or locally.
Write-Host "Checking for Chromium Engine..."
$env:PLAYWRIGHT_BROWSERS_PATH = "$PSScriptRoot\bin"
.\venv\Scripts\python.exe -m playwright install chromium

# 5. Patch Executable Icon & Deep Metadata (Agentica Name)
Write-Host "Configuring Executable Metadata & Icon..."
$SetupScript = @"
import os, shutil, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

os.environ['PLAYWRIGHT_BROWSERS_PATH'] = r'$PSScriptRoot\bin'
with sync_playwright() as p:
    original = Path(p.chromium.executable_path)
    agentica = original.parent / 'agentica.exe'
    shutil.copy2(original, agentica)
    
    rcedit = Path(r'$PSScriptRoot\rcedit-x64.exe')
    icon = Path(r'$PSScriptRoot\agentica.ico')
    if rcedit.exists() and icon.exists():
        cmd = [
            str(rcedit),
            str(agentica),
            '--set-version-string', 'FileDescription', 'Agentica',
            '--set-version-string', 'ProductName', 'Agentica',
            '--set-version-string', 'OriginalFilename', 'agentica.exe',
            '--set-icon', str(icon)
        ]
        subprocess.run(cmd, capture_output=True)
"@
.\venv\Scripts\python.exe -c $SetupScript

# Run deep binary patch to eliminate Google strings from chrome.dll and locales
if (Test-Path "$PSScriptRoot\deep_patch.py") {
    Write-Host "Applying deep binary branding..."
    .\venv\Scripts\python.exe "$PSScriptRoot\deep_patch.py"
}

# 6. Generate the Launcher Batch File
Write-Host "Creating Launchers..."
$BatContent = "@echo off`r`nset PLAYWRIGHT_BROWSERS_PATH=%~dp0bin`r`nstart """" /B `"%~dp0venv\Scripts\python.exe`" `"%~dp0src\human\launcher.py`""
Set-Content -Path "$PSScriptRoot\Agentica.bat" -Value $BatContent

Write-Host "========================================="
Write-Host " Setup Complete! You can close this window. " -ForegroundColor Green
Write-Host "========================================="
Start-Sleep -Seconds 3
