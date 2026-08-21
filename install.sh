#!/bin/bash
echo "=== AgenPulsa Auto-Installer (Linux/Mac) ==="

# Cek Python
if ! command -v python3 &> /dev/null
then
    echo "Python3 tidak ditemukan. Harap install Python3 dan pip."
    exit 1
fi

echo "[1/4] Menginstall dependencies Python..."
python3 -m pip install -r requirements.txt

echo "[2/4] Menginstall Chromium untuk Playwright..."
python3 -m playwright install chromium

echo "[3/4] Menyiapkan environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "File .env berhasil dibuat dari template."
else
    echo "File .env sudah ada."
fi

if [ ! -d "profile" ]; then
    mkdir profile
    echo "Folder profile/ disiapkan."
fi

if [ ! -f shortcuts.json ]; then
    echo "[]" > shortcuts.json
fi

echo "[4/4] Instalasi Selesai!"
echo ""
echo "Cara Penggunaan di VPS/No-GUI:"
echo "1. Pindahkan folder 'profile' yang sudah login dari PC kamu ke folder ini."
echo "2. Edit file .env dengan token Telegram-mu."
echo "3. Jalankan bot: python3 tgbot.py"
