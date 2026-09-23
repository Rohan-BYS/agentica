# Agentica One-Click Installer
Write-Host "========================================="
Write-Host "       Installing Agentica Browser       "
Write-Host "========================================="

# 1. Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from python.org and run this script again."
    exit
}

$InstallDir = "$env:USERPROFILE\AgenticaBrowser"
if (-not (Test-Path $InstallDir)) {
    Write-Host "Cloning Agentica to $InstallDir..."
    # In a real scenario, this would be: git clone https://github.com/yourusername/agentica.git $InstallDir
    # For now, we assume the user unzipped it or we download the zip.
}

Set-Location $InstallDir

# 2. Install Python Requirements (Skipped if already installed)
Write-Host "Checking and installing Python dependencies..."
python -m pip install -r requirements.txt

# 3. Install Playwright Chromium (Smart Install)
# By default, Playwright checks if Chromium is already downloaded in the system. 
# If it is, it skips the 700MB download entirely!
Write-Host "Ensuring Chromium engine is present..."
python -m playwright install chromium

# 4. Patch the Executable for the Task Manager (Agentica name & icon)
Write-Host "Configuring Agentica Executable..."
$SetupScript = @"
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    original = Path(p.chromium.executable_path)
    agentica = original.parent / 'agentica.exe'
    if not agentica.exists():
        shutil.copy2(original, agentica)
    
    # We use rcedit to patch it if available
    rcedit_path = Path('rcedit-x64.exe')
    if rcedit_path.exists():
        os.system(f'{rcedit_path} {agentica} --set-version-string "FileDescription" "Agentica" --set-icon agentica.ico')
"@
python -c $SetupScript

# 5. Create Desktop Shortcut
Write-Host "Creating Desktop Shortcut..."
$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut("$env:USERPROFILE\Desktop\Agentica.lnk")
$shortcut.TargetPath = "$InstallDir\Agentica.bat"
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Description = "Agentica AI Browser"
$shortcut.IconLocation = "$InstallDir\agentica.ico"
$shortcut.Save()

Write-Host "========================================="
Write-Host " Installation Complete! " -ForegroundColor Green
Write-Host " You can now double-click Agentica on your Desktop."
Write-Host "========================================="
Start-Sleep -Seconds 3
