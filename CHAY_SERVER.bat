@echo off
title MAY CHU GIAM SAT GIAY VE SINH (FASTAPI)
echo ============================================================
echo   DANG KHOI DONG HE THONG GIAM SAT GIAY VE SINH...
echo ============================================================

rem Tu dong tat tien trinh cu neu co de tranh trung port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [THONG BAO] Phat hien tien trinh cu (PID %%a) dang chiem port 8000, dang giai phong...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo   Dia chi Web Dashboard : http://localhost:8000
echo   Tai khoan mac dinh    : admin / admin123
echo ============================================================
echo.
cd /d "%~dp0"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
