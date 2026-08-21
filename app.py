import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, "profile")
BASE = "https://isipulsa.web.id/"


def cek_status():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=True, viewport={"width": 1366, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            header = page.locator("header").inner_text()
            if "Masuk" in header and "Saldo" not in header:
                return False, "-"
            saldo = header.replace("Saldo Deposit", "").strip() or "Rp 0"
            return True, saldo
        finally:
            ctx.close()


def login_manual():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False, viewport={"width": 1366, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        input("Login manual di browser. Tekan Enter kalau sudah...")
        ctx.close()


class App:
    def __init__(self, root):
        self.root = root
        root.title("AgenPulsa")
        root.geometry("480x420")
        root.resizable(False, False)

        self.bot_proc = None

        tk.Label(root, text="AgenPulsa Dashboard", font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))

        frame = tk.LabelFrame(root, text="Status", padx=10, pady=8)
        frame.pack(fill="x", padx=16, pady=6)
        self.lbl_login = tk.Label(frame, text="Login: mengecek...", anchor="w", font=("Segoe UI", 11))
        self.lbl_login.pack(fill="x")
        self.lbl_saldo = tk.Label(frame, text="Saldo: -", anchor="w", font=("Segoe UI", 11))
        self.lbl_saldo.pack(fill="x")
        self.lbl_bot = tk.Label(frame, text="Bot Telegram: mati", anchor="w", font=("Segoe UI", 11))
        self.lbl_bot.pack(fill="x")

        btns = tk.Frame(root)
        btns.pack(pady=8)
        tk.Button(btns, text="1. Cek Status", width=16, command=self.on_cek).grid(row=0, column=0, padx=4, pady=3)
        tk.Button(btns, text="2. Cek Telegram", width=16, command=self.on_telegram).grid(row=0, column=1, padx=4, pady=3)
        tk.Button(btns, text="3. Logout", width=16, command=self.on_logout).grid(row=1, column=0, padx=4, pady=3)
        tk.Button(btns, text="Login", width=16, command=self.on_login).grid(row=1, column=1, padx=4, pady=3)
        tk.Button(btns, text="Install Chromium", width=16, command=self.on_install).grid(row=2, column=0, padx=4, pady=3)

        self.log = scrolledtext.ScrolledText(root, height=10, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        self.on_cek()

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def on_cek(self):
        self.lbl_login.config(text="Login: mengecek...")
        self.write_log("Cek status...")

        def work():
            try:
                login, saldo = cek_status()
            except Exception as e:
                self.root.after(0, lambda: self.write_log(f"ERROR cek status: {e}"))
                login, saldo = False, "-"
            self.root.after(0, lambda: self.update_status(login, saldo))

        threading.Thread(target=work, daemon=True).start()

    def update_status(self, login, saldo):
        self.lbl_login.config(text=f"Login: {'YA' if login else 'TIDAK'}", fg="green" if login else "red")
        self.lbl_saldo.config(text=f"Saldo: {saldo}")
        self.write_log(f"Login: {'YA' if login else 'TIDAK'} | Saldo: {saldo}")

    def on_telegram(self):
        if self.bot_proc and self.bot_proc.poll() is None:
            self.write_log("Bot Telegram sudah jalan. Klik lagi untuk stop.")
            self.bot_proc.terminate()
            self.bot_proc = None
            self.lbl_bot.config(text="Bot Telegram: mati", fg="black")
            return
        
        # Cek token dari .env
        import os
        from dotenv import load_dotenv
        env_path = os.path.join(HERE, ".env")
        load_dotenv(env_path)
        token = os.getenv("TELEGRAM_TOKEN", "")
        
        if not token or "ISI_TOKEN" in token:
            messagebox.showwarning("AgenPulsa", "TELEGRAM_TOKEN belum diisi di file .env")
            return
            
        self.bot_proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "tgbot.py")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.lbl_bot.config(text="Bot Telegram: jalan", fg="green")
        self.write_log("Bot Telegram dijalankan.")

        def pump():
            for line in self.bot_proc.stdout:
                self.root.after(0, lambda l=line.rstrip(): self.write_log(f"[bot] {l}"))
            self.root.after(0, lambda: self.lbl_bot.config(text="Bot Telegram: mati", fg="black"))

        threading.Thread(target=pump, daemon=True).start()

    def on_logout(self):
        if not messagebox.askyesno("AgenPulsa", "Logout akan hapus sesi login (folder profile). Lanjut?"):
            return
        if os.path.exists(PROFILE):
            shutil.rmtree(PROFILE, ignore_errors=True)
        self.write_log("Logout: sesi dihapus. Klik Login untuk masuk lagi.")
        self.update_status(False, "-")

    def on_login(self):
        self.write_log("Buka browser untuk login manual...")

        def work():
            try:
                login_manual()
            except Exception as e:
                self.root.after(0, lambda: self.write_log(f"ERROR login: {e}"))
            self.root.after(0, self.on_cek)

        threading.Thread(target=work, daemon=True).start()

    def on_install(self):
        self.write_log("Install Chromium (bisa beberapa menit)...")

        def work():
            proc = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True, text=True,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            for line in out.strip().splitlines():
                self.root.after(0, lambda l=line: self.write_log(f"[install] {l}"))
            if proc.returncode == 0:
                self.root.after(0, lambda: self.write_log("Install Chromium SELESAI."))
            else:
                self.root.after(0, lambda: self.write_log("Install Chromium GAGAL. Coba lagi atau cek koneksi."))

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
