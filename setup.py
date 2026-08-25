import os
import sys
import platform
import subprocess

def run(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True)

def main():
    print("=== Setup AgenPulsa Auto-Installer ===")
    os_name = platform.system()
    print(f"OS Terdeteksi: {os_name}")

    # Linux distro modern (PEP 668) menolak pip install ke system python.
    # Solusi: semua install masuk venv .venv/ di folder proyek.
    if os_name == "Linux":
        venv_dir = os.path.join(os.getcwd(), ".venv")
        py = os.path.join(venv_dir, "bin", "python")
        if not os.path.exists(py):
            print("\n[0/4] Membuat virtual environment (.venv)...")
            r = subprocess.run([sys.executable, "-m", "venv", venv_dir])
            if r.returncode != 0:
                print("Gagal membuat venv. Jalankan dulu: sudo apt install python3-venv")
                return
    else:
        py = sys.executable

    print("\n[1/4] Menginstall Dependensi Python...")
    run(f'"{py}" -m pip install -r requirements.txt')

    print("\n[2/4] Menginstall Chromium (Playwright)...")
    if os_name == "Linux":
        run(f'"{py}" -m playwright install --with-deps chromium')
    else:
        run(f'"{py}" -m playwright install chromium')
    
    print("\n[3/4] Menyiapkan File Konfigurasi...")
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("TELEGRAM_TOKEN=ISI_TOKEN_BOT_DISINI\nALLOWED_IDS=\n")
        print("File .env berhasil dibuat dari template.")
    else:
        print("File .env sudah ada, dilewati.")
        
    if not os.path.exists("shortcuts.json"):
        with open("shortcuts.json", "w") as f:
            f.write("[]")
            
    if not os.path.exists("profile"):
        os.makedirs("profile")
        
    print("\n[4/4] Konfigurasi Latar Belakang (Background Service)")
    if os_name == "Linux":
        print("Pilih service manager untuk menjalankan bot non-stop:")
        print("1. Systemd (Default Linux Server, Direkomendasikan)")
        print("2. PM2 (Membutuhkan NodeJS terinstall)")
        print("3. Lewati (Jalankan manual)")
        pil = input("Pilihan (1/2/3): ").strip()
        
        if pil == "1":
            user = os.getenv("USER", "root")
            cwd = os.getcwd()
            svc = f"""[Unit]
Description=AgenPulsa Telegram Bot
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={cwd}
ExecStart={py} tgbot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
            with open("agenpulsa.service", "w") as f:
                f.write(svc)
            print("\n[INFO] File 'agenpulsa.service' telah dibuat.")
            print("Untuk mengaktifkannya, jalankan perintah berikut:")
            print("  sudo cp agenpulsa.service /etc/systemd/system/")
            print("  sudo systemctl daemon-reload")
            print("  sudo systemctl enable agenpulsa")
            print("  sudo systemctl start agenpulsa")
            print("Cek status: sudo systemctl status agenpulsa")
            
        elif pil == "2":
            run(f"pm2 start tgbot.py --interpreter {py} --name agenpulsa")
            run("pm2 save")
            run("pm2 startup")
            
    elif os_name == "Windows":
        print("Pilih service manager untuk latar belakang:")
        print("1. PM2 (Membutuhkan NodeJS: npm install pm2 -g)")
        print("2. Lewati (Jalankan via GUI)")
        pil = input("Pilihan (1/2): ").strip()
        
        if pil == "1":
            run(f"pm2 start tgbot.py --interpreter {py} --name agenpulsa")
            run("pm2 save")
            
    print("\n=== Instalasi Selesai! ===")
    print("Silakan edit file .env dan isi token bot Telegram-mu.")

if __name__ == "__main__":
    main()
