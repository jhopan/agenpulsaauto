@echo off
echo === AgenPulsa Auto-Installer (Windows) ===

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python tidak ditemukan! Harap install Python dan tambahkan ke PATH.
    pause
    exit /b
)

echo [1/4] Menginstall dependencies Python...
pip install -r requirements.txt

echo [2/4] Menginstall Chromium untuk Playwright...
python -m playwright install chromium

echo [3/4] Menyiapkan environment...
if not exist .env (
    copy .env.example .env >nul
    echo File .env berhasil dibuat.
) else (
    echo File .env sudah ada.
)

if not exist "profile" mkdir "profile"
if not exist shortcuts.json echo [] > shortcuts.json

echo [4/4] Instalasi Selesai!
echo.
echo Lanjut:
echo 1. Isi file .env dengan token Telegram-mu
echo 2. Ketik 'menuagenpulsa' untuk membuka dashboard.
pause
