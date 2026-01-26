#Requires -Version 5.1
<#
.SYNOPSIS
    Project Memory Skill - Windows PowerShell Installer
.DESCRIPTION
    Installs the Project Memory skill commands for easy access
#>

Write-Host "========================================"
Write-Host "  Project Memory Skill Installer"
Write-Host "  Platform: Windows (PowerShell)"
Write-Host "========================================"
Write-Host

# Check Python
Write-Host "[1/4] Checking Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      $pythonVersion found"
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check MemOS
Write-Host
Write-Host "[2/4] Checking MemOS..."
$memosUrl = if ($env:MEMOS_URL) { $env:MEMOS_URL } else { "http://localhost:18000" }
try {
    $response = Invoke-WebRequest -Uri $memosUrl -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
    Write-Host "      MemOS available at $memosUrl"
} catch {
    Write-Host "      WARNING: MemOS not responding at $memosUrl" -ForegroundColor Yellow
    Write-Host "      Make sure to start MemOS before using the skill"
}

# Create commands directory
Write-Host
Write-Host "[3/4] Creating command shortcuts..."
$binDir = "$env:USERPROFILE\.local\bin"
$skillDir = "$env:USERPROFILE\.claude\skills\project-memory"

if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

# Create PowerShell wrapper functions
$profileContent = @"

# Project Memory Skill Commands
function memos-save { python "`$env:USERPROFILE\.claude\skills\project-memory\scripts\memos_save.py" `$args }
function memos-search { python "`$env:USERPROFILE\.claude\skills\project-memory\scripts\memos_search.py" `$args }
function memos-init { python "`$env:USERPROFILE\.claude\skills\project-memory\scripts\memos_init_project.py" `$args }
"@

# Also create .cmd files for cmd.exe compatibility
@"
@echo off
python "%USERPROFILE%\.claude\skills\project-memory\scripts\memos_save.py" %*
"@ | Out-File -FilePath "$binDir\memos-save.cmd" -Encoding ASCII

@"
@echo off
python "%USERPROFILE%\.claude\skills\project-memory\scripts\memos_search.py" %*
"@ | Out-File -FilePath "$binDir\memos-search.cmd" -Encoding ASCII

@"
@echo off
python "%USERPROFILE%\.claude\skills\project-memory\scripts\memos_init_project.py" %*
"@ | Out-File -FilePath "$binDir\memos-init.cmd" -Encoding ASCII

Write-Host "      Commands installed to $binDir"

# Check/Update PowerShell Profile
Write-Host
Write-Host "[4/4] Configuring PowerShell profile..."
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath -Parent

if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

if (-not (Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

$existingProfile = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
if ($existingProfile -notlike "*memos-save*") {
    Add-Content -Path $profilePath -Value $profileContent
    Write-Host "      PowerShell profile updated"
} else {
    Write-Host "      PowerShell profile already configured"
}

# Check PATH for cmd.exe
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    Write-Host "      WARNING: $binDir is not in PATH" -ForegroundColor Yellow
    $addToPath = Read-Host "      Add to PATH? (Y/n)"
    if ($addToPath -ne "n") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
        Write-Host "      PATH updated (restart terminal to apply)"
    }
} else {
    Write-Host "      PATH OK"
}

Write-Host
Write-Host "========================================"
Write-Host "  Installation Complete!"
Write-Host "========================================"
Write-Host
Write-Host "Usage:"
Write-Host "  memos-init                    # Initialize current project"
Write-Host "  memos-save `"content`" -t TYPE  # Save a memory"
Write-Host "  memos-search `"query`"          # Search memories"
Write-Host
Write-Host "Restart your terminal to use the commands."
Write-Host
