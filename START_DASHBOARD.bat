@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Zen-Genie Dashboard - Baslatiliyor
echo.
echo  ======================================
echo   Zen-Genie - Faz 1 Dashboard
echo  ======================================
echo.

:: ── 1. Docker var mi? ──
where docker >nul 2>&1
if errorlevel 1 (
  echo  [HATA] Docker bulunamadi.
  echo  Docker Desktop kurulu degil veya PATH'te degil.
  echo  Lutfen https://www.docker.com/products/docker-desktop/ adresinden kurun.
  echo.
  pause
  exit /b 1
)

:: ── 2. Docker calisiyor mu? ──
docker info >nul 2>&1
if not errorlevel 1 goto :docker_ready

echo  Docker henuz hazir degil - Docker Desktop baslatiliyor...
set "DD1=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set "DD2=%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"
if exist "!DD1!" start "" "!DD1!"
if exist "!DD2!" start "" "!DD2!"
if not exist "!DD1!" if not exist "!DD2!" (
  echo  [HATA] Docker Desktop bulunamadi.
  echo  Docker Desktop'i manuel baslatin ve tekrar deneyin.
  echo.
  pause
  exit /b 1
)
echo  Docker aciliyor, bekleniyor (en fazla 90 sn)...
for /L %%i in (1,1,30) do (
  timeout /t 3 /nobreak >nul
  docker info >nul 2>&1
  if not errorlevel 1 goto :docker_ready
  echo    ... bekleniyor %%i/30
)
echo  [HATA] Docker baslatilamadi / zaman asimi.
echo  Docker Desktop'i acip "Engine running" gorunene kadar bekleyin.
echo.
pause
exit /b 1

:docker_ready
echo  [OK] Docker hazir

:: ── 3. Zaten calisiyorsa dogrudan tarayici ac ──
curl -s -m 2 http://127.0.0.1:5173 >nul 2>&1
if not errorlevel 1 (
  docker ps --filter "name=zen-dashboard" --filter "status=running" --format "{{.Names}}" 2>nul | C:\Windows\System32\findstr.exe /i "zen-dashboard" >nul 2>&1
  if not errorlevel 1 (
    echo  [OK] Dashboard zaten calisiyor - tarayici aciliyor...
    start "" "http://127.0.0.1:5173"
    echo  Dashboard: http://127.0.0.1:5173  ^|  API: http://127.0.0.1:8001/docs
    timeout /t 3 >nul
    exit /b 0
  )
)

:: ── 4. Container'lari baslat / build et (sessiz) ──
echo  Dashboard baslatiliyor (ilk acilista 1-2 dk surebilir)...
set "LOG=%TEMP%\zen-genie-dashboard.log"
docker compose up -d --build dashboard-api dashboard > "%LOG%" 2>&1
if errorlevel 1 (
  echo  [HATA] Dashboard baslatilamadi.
  echo  Neden: Docker build/up hatasi. Log: %LOG%
  echo  --- son 20 satir ---
  powershell -NoProfile -Command "Get-Content '%LOG%' | Select-Object -Last 20" 2>nul
  echo.
  echo  Cozum: Docker Desktop'in calistigindan ve port 5173/8001'in bosta oldugundan emin olun.
  echo  Port kontrol: netstat -ano ^| findstr ":5173 :8001"
  echo.
  pause
  exit /b 1
)

:: ── 5. Hazir olana kadar bekle ──
echo  Servisler hazirlaniyor, bekleniyor...
for /L %%i in (1,1,40) do (
  timeout /t 3 /nobreak >nul
  curl -s -m 2 http://127.0.0.1:5173 >nul 2>&1
  if not errorlevel 1 goto :ready
  if %%i==10 echo    ... hala hazirlaniyor (%%i/40)
  if %%i==20 echo    ... biraz daha bekleniyor (%%i/40)
)
echo  [HATA] Dashboard zamaninda hazir olmadi.
echo  Durum kontrol ediliyor...
docker ps --format "table {{.Names}}  {{.Status}}  {{.Ports}}" 2>nul
echo.
echo  Log: %LOG%
powershell -NoProfile -Command "Get-Content '%LOG%' | Select-Object -Last 20" 2>nul
echo.
pause
exit /b 1

:ready
:: ── 6. Freqtrade uyari (bloklamaz) ──
docker ps --filter "name=ai-trader-dryrun" --filter "status=running" --format "{{.Names}}" 2>nul | C:\Windows\System32\findstr.exe /i "ai-trader-dryrun" >nul 2>&1
if errorlevel 1 (
  echo  [UYARI] Freqtrade dry-run calismiyor gorunuyor.
  echo          Dashboard acilacak ama bot verisi gosterilmeyebilir.
  echo          Kontrol: docker ps | findstr ai-trader-dryrun
  echo.
)

echo  [OK] Dashboard hazir!
echo  Aciliyor: http://127.0.0.1:5173
start "" "http://127.0.0.1:5173"
echo  API: http://127.0.0.1:8001/docs
echo.
echo  Kapatmak icin STOP_DASHBOARD.bat cift tiklayin.
timeout /t 4 >nul
exit /b 0