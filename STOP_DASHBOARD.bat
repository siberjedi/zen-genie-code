@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Zen-Genie Dashboard — Durduruluyor

echo.
echo  Zen-Genie Dashboard durduruluyor...
echo  (Freqtrade dry-run calismaya devam edecek)
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo  [HATA] Docker bulunamadi.
  pause
  exit /b 1
)

docker compose stop dashboard dashboard-api >nul 2>&1
if errorlevel 1 (
  docker stop zen-dashboard zen-dashboard-api >nul 2>&1
)

echo  [OK] Dashboard durduruldu.
echo  Freqtrade durumu:
docker ps --filter "name=ai-trader-dryrun" --format "  {{.Names}}  {{.Status}}" 2>nul
if errorlevel 1 echo    kontrol edilemedi
echo.
echo  Tekrar acmak icin START_DASHBOARD.bat cift tiklayin.
timeout /t 3 >nul
exit /b 0
