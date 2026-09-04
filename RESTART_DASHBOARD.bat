@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Zen-Genie Dashboard — Yeniden Baslatiliyor

echo.
echo  Zen-Genie Dashboard yeniden baslatiliyor...
echo  (Freqtrade'e dokunulmayacak)
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo  [HATA] Docker bulunamadi.
  pause
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo  [HATA] Docker calismiyor. Once Docker Desktop'i baslatin.
  pause
  exit /b 1
)

set "LOG=%TEMP%\zen-genie-restart.log"
docker compose up -d --build dashboard-api dashboard > "%LOG%" 2>&1
if errorlevel 1 (
  echo  [HATA] Yeniden baslatilamadi. Log: %LOG%
  powershell -NoProfile -Command "Get-Content '%LOG%' | Select-Object -Last 20" 2>nul
  pause
  exit /b 1
)

echo  Hazir olmasi bekleniyor...
for /L %%i in (1,1,20) do (
  timeout /t 3 /nobreak >nul
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0}else{exit 1}} catch {exit 1}" >nul 2>&1
  if not errorlevel 1 goto :ok
)
echo  [UYARI] Zaman asimi ama servisler ayaga kalkmis olabilir.
docker ps --filter "name=zen-dashboard" --format "  {{.Names}}  {{.Status}}" 2>nul
pause
exit /b 1

:ok
echo  [OK] Dashboard yeniden baslatildi: http://127.0.0.1:5173
start "" "http://127.0.0.1:5173"
timeout /t 3 >nul
exit /b 0
