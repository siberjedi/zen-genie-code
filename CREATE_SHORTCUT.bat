@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0"
title Zen-Genie — Kisayol Olustur
echo.
echo  Masaustune kisayol olusturuluyor...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $target=Join-Path $PSScriptRoot 'START_DASHBOARD.bat'; $lnk=Join-Path $desktop 'Zen-Genie Dashboard.lnk'; $Wsh=New-Object -COM WScript.Shell; $sc=$Wsh.CreateShortcut($lnk); $sc.TargetPath=$target; $sc.WorkingDirectory=$PSScriptRoot; $sc.Description='Zen-Genie Faz 1 Dashboard - cift tikla ac'; $sc.IconLocation='%SystemRoot%\System32\SHELL32.dll,14'; $sc.Save(); Write-Host '[OK] Kisayol:' $lnk -ForegroundColor Green"
if errorlevel 1 (
  echo  [HATA] Kisayol olusturulamadi.
  echo  Manuel: START_DASHBOARD.bat'e sag tik ^> Gonder ^> Masaustu (kisayol olustur)
  pause
  exit /b 1
)
echo.
echo  Hazir! Masaustundeki "Zen-Genie Dashboard" kisayoluna cift tiklayin.
echo.
pause
exit /b 0
