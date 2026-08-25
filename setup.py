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
        token = input("Masukkan Token Bot Telegram (dari BotFather): ").strip()
        allowed = input("Masukkan ID Telegram yang diizinkan (pisahkan koma, kosong = semua): ").strip()
        with open(".env", "w") as f:
            f.write(f"TELEGRAM_TOKEN={token or 'ISI_TOKEN_BOT_DISINI'}\nALLOWED_IDS={allowed}\n")
        print("File .env berhasil dibuat.")
    else:
        print("File .env sudah ada, dilewati.")
        
    if not os.path.exists("shortcuts.json"):
        with open("shortcuts.json", "w") as f:
            f.write("[]")
            
    if not os.path.exists("profile"):
        os.makedirs("profile")
        
    print("\n[4/4] Konfigurasi Latar Belakang (Background Service)")
    if os_name == "Linux":
        cwd = os.getcwd()

        # Pasang menuagenpulsa ke PATH supaya bisa dipanggil dari folder mana saja.
        menu_src = os.path.join(cwd, "menuagenpulsa")
        if os.path.exists(menu_src):
            content = open(menu_src, encoding="utf-8").read()
            content = content.replace("APP_DIR=${APP_DIR:-/root/agenpulsa}", f"APP_DIR=${{APP_DIR:-{cwd}}}")
            tmp = os.path.join(cwd, ".menuagenpulsa.tmp")
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.chmod(tmp, 0o755)
            r = subprocess.run(["cp", tmp, "/usr/local/bin/menuagenpulsa"])
            if r.returncode != 0:
                subprocess.run(["sudo", "cp", tmp, "/usr/local/bin/menuagenpulsa"])
            os.remove(tmp)
            print("menuagenpulsa terpasang ke /usr/local/bin (langsung bisa dipanggil).")

            # Helper login via virtual display (dipakai menuagenpulsa opsi login).
            login_script = f"""#!/bin/sh
set -eu
systemctl stop agenpulsa.service 2>/dev/null || true
trap "systemctl start agenpulsa.service" EXIT INT TERM
cd {cwd}
DISPLAY=:99 {py} bot.py --login
"""
            tmp2 = os.path.join(cwd, ".agenpulsa-login.tmp")
            with open(tmp2, "w", encoding="utf-8", newline="\n") as f:
                f.write(login_script)
            os.chmod(tmp2, 0o700)
            r = subprocess.run(["cp", tmp2, "/usr/local/bin/agenpulsa-login"])
            if r.returncode != 0:
                subprocess.run(["sudo", "cp", tmp2, "/usr/local/bin/agenpulsa-login"])
            os.remove(tmp2)

            # VNC login on-demand (opsi 6 menu).
            import shutil
            vnc_ready = all(shutil.which(b) for b in ("Xvfb", "x11vnc", "websockify"))
            if not vnc_ready:
                jawab = input("\nInstall VNC untuk login via browser virtual? (y/n): ").strip().lower()
                if jawab == "y":
                    print("[INFO] Menginstall VNC stack (xvfb, x11vnc, novnc, websockify)...")
                    r = subprocess.run("apt-get install -y xvfb x11vnc novnc websockify", shell=True)
                    if r.returncode != 0:
                        subprocess.run("sudo apt-get install -y xvfb x11vnc novnc websockify", shell=True)
                    vnc_ready = all(shutil.which(b) for b in ("Xvfb", "x11vnc", "websockify"))
            if vnc_ready:
                vnc_units = {
                    "agenpulsa-display.service": """[Unit]
Description=Virtual display for AgenPulsa login

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1366x900x24 -nolisten tcp
Restart=always

[Install]
WantedBy=multi-user.target
""",
                    "agenpulsa-vnc.service": """[Unit]
Description=Local VNC for AgenPulsa login
After=agenpulsa-display.service
Requires=agenpulsa-display.service

[Service]
Type=simple
ExecStart=/usr/bin/x11vnc -display :99 -rfbauth /root/.vnc/agenpulsa.pass -localhost -forever -shared
Restart=always

[Install]
WantedBy=multi-user.target
""",
                    "agenpulsa-novnc.service": """[Unit]
Description=Local noVNC for AgenPulsa login
After=agenpulsa-vnc.service
Requires=agenpulsa-vnc.service

[Service]
Type=simple
ExecStart=/usr/bin/websockify --web /usr/share/novnc 0.0.0.0:6080 localhost:5900
Restart=always

[Install]
WantedBy=multi-user.target
""",
                }
                os.makedirs("/root/.vnc", mode=0o700, exist_ok=True)
                if not os.path.exists("/root/.vnc/agenpulsa.pass"):
                    subprocess.run("x11vnc -storepasswd agenpulsa /root/.vnc/agenpulsa.pass",
                                   shell=True, capture_output=True)
                for name, body in vnc_units.items():
                    dest = f"/etc/systemd/system/{name}"
                    if not os.path.exists(dest):
                        with open(f".{name}.tmp", "w", newline="\n") as f:
                            f.write(body)
                        r = subprocess.run(["cp", f".{name}.tmp", dest])
                        if r.returncode != 0:
                            subprocess.run(["sudo", "cp", f".{name}.tmp", dest])
                        os.remove(f".{name}.tmp")
                subprocess.run("systemctl daemon-reload", shell=True, capture_output=True)
                print("VNC login on-demand terpasang (tidak auto-start, hanya saat menu login).")
            else:
                print("[INFO] Login via VNC butuh: sudo apt install -y xvfb x11vnc novnc websockify")

        # Deteksi service yang sudah terpasang supaya tidak double.
        existing = []
        for name in ("agenpulsa", "agenpulsaauto"):
            unit = f"/etc/systemd/system/{name}.service"
            if os.path.exists(unit):
                existing.append(name)
        if existing:
            print(f"\n[INFO] Service sudah terpasang: {', '.join(existing)}.")
            print("Setup akan memperbarui unit file dan tidak membuat duplikat.")

        print("\nPilih service manager untuk menjalankan bot non-stop:")
        print("1. Systemd (Default Linux Server, Direkomendasikan)")
        print("2. PM2 (Membutuhkan NodeJS terinstall)")
        print("3. Lewati (Jalankan manual)")
        pil = input("Pilihan (1/2/3): ").strip()
        
        if pil == "1":
            user = os.getenv("USER", "root")
            # Pakai nama service yang sudah ada supaya tidak double.
            svc_name = existing[0] if existing else "agenpulsa"
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
            with open(f"{svc_name}.service", "w") as f:
                f.write(svc)
            if svc_name in existing:
                print(f"[INFO] Service '{svc_name}' sudah ada. Memperbarui unit file...")
            else:
                print(f"[INFO] File '{svc_name}.service' dibuat. Memasang otomatis...")
            for c in (f"cp {svc_name}.service /etc/systemd/system/{svc_name}.service",
                      "systemctl daemon-reload",
                      f"systemctl enable {svc_name}"):
                r = subprocess.run(c, shell=True)
                if r.returncode != 0:
                    subprocess.run(f"sudo {c}", shell=True)

            env_token = ""
            if os.path.exists(".env"):
                for line in open(".env", encoding="utf-8"):
                    if line.startswith("TELEGRAM_TOKEN="):
                        env_token = line.split("=", 1)[1].strip()
            if env_token and "ISI_TOKEN" not in env_token:
                r = subprocess.run(f"systemctl restart {svc_name}", shell=True)
                if r.returncode != 0:
                    subprocess.run(f"sudo systemctl restart {svc_name}", shell=True)
                subprocess.run(f"systemctl --no-pager status {svc_name}", shell=True)
            else:
                print(f"\n[INFO] Token bot belum diisi di .env. Setelah diisi, aktifkan dengan:")
                print(f"  sudo systemctl start {svc_name}")
            
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
