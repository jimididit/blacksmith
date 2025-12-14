# Blacksmith Uninstallation Script for Windows

$ErrorActionPreference = "Stop"

Write-Host "🔨 Blacksmith Uninstallation Script" -ForegroundColor Blue
Write-Host ""

# Check if blacksmith is installed
if (-not (Get-Command blacksmith -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Blacksmith does not appear to be installed." -ForegroundColor Yellow
    exit 0
}

Write-Host "✓ Found Blacksmith installation" -ForegroundColor Green

# Find pip command
$pipCmd = $null
if (Get-Command pip -ErrorAction SilentlyContinue) {
    $pipCmd = "pip"
} elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
    $pipCmd = "pip3"
} else {
    Write-Host "✗ pip not found. Cannot uninstall automatically." -ForegroundColor Red
    exit 1
}

# Confirm uninstallation
Write-Host ""
$confirm = Read-Host "Are you sure you want to uninstall Blacksmith? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Uninstallation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Uninstalling Blacksmith..." -ForegroundColor Blue

# Try different uninstall methods
$success = $false

# Method 1: pip uninstall
try {
    $packageInfo = & $pipCmd show blacksmith 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Attempting uninstall with $pipCmd..."
        & $pipCmd uninstall -y blacksmith 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
    }
} catch {
    # Continue to next method
}

# Method 2: pip uninstall --user
if (-not $success) {
    try {
        Write-Host "Attempting uninstall with $pipCmd --user..."
        & $pipCmd uninstall -y --user blacksmith 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
    } catch {
        # Continue
    }
}

# Verify uninstallation
if (Get-Command blacksmith -ErrorAction SilentlyContinue) {
    Write-Host "⚠ Blacksmith command still found. Manual removal may be required." -ForegroundColor Yellow
    Write-Host "Try running:"
    Write-Host "  $pipCmd uninstall blacksmith"
    Write-Host "  $pipCmd uninstall --user blacksmith"
    exit 1
} elseif ($success) {
    Write-Host "✓ Blacksmith uninstalled successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Could not automatically uninstall Blacksmith." -ForegroundColor Red
    Write-Host "Please try manually:"
    Write-Host "  $pipCmd uninstall blacksmith"
    Write-Host "  $pipCmd uninstall --user blacksmith"
    exit 1
}

