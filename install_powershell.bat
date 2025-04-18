@echo off
setlocal enabledelayedexpansion

echo Installing Ager for PowerShell...

REM Create a PowerShell profile directory if it doesn't exist
powershell -Command "if (!(Test-Path -Path $PROFILE -PathType Container)) { New-Item -ItemType Directory -Path (Split-Path -Parent $PROFILE) -Force | Out-Null }"

REM Copy the PowerShell module to the user's modules folder
powershell -Command "$modulesPath = Join-Path (Split-Path -Parent $PROFILE) 'Modules\\Ager'; if (!(Test-Path -Path $modulesPath)) { New-Item -ItemType Directory -Path $modulesPath -Force | Out-Null }; Copy-Item -Path '%~dp0Ager.psm1' -Destination $modulesPath -Force; Write-Output 'Copied module to PowerShell modules folder'"

REM Add the module import to the profile if it doesn't exist
powershell -Command "if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }; if (-not (Select-String -Path $PROFILE -Pattern 'Import-Module Ager' -Quiet)) { Add-Content -Path $PROFILE -Value 'Import-Module Ager' -Force; Write-Output 'Added module import to PowerShell profile' }"

echo.
echo Installation complete! Please restart your PowerShell session.
echo You can now use 'ager' commands directly in PowerShell.

pause
endlocal 