# AgenPulsa

Bot otomatisasi pembelian pulsa/paket kuota dari [isipulsa.web.id](https://isipulsa.web.id/).

## Fitur

- Cari paket berdasarkan kata kunci atau ID voucher.
- Beli paket via command line, GUI Windows, atau bot Telegram.
- Shortcut paket, kontak pelanggan, dan jadwal auto harian, sekali, atau interval.
- Cek status login dan saldo deposit.
- Semua jadwal memakai zona waktu WIB (`Asia/Jakarta`).
- Transaksi manual dan auto dibatalkan pada 23:40-00:35 WIB untuk rekap situs.
- Dashboard terminal Linux: status, log, backup, dan login ulang via VNC sementara.

## Struktur

```
app.py                  # GUI dashboard tkinter (Windows)
bot.py                  # engine order Playwright
menuagenpulsa           # dashboard terminal Linux
menuagenpulsa.bat       # launcher GUI Windows
tgbot.py                # bot Telegram
shortcuts.json          # daftar shortcut paket
contacts.json           # kontak runtime (dibuat otomatis)
schedules.json          # jadwal runtime (dibuat otomatis)
profile/                # profile/cookie browser setelah login
```

## Instalasi lokal

```bash
python setup.py
```

Script memasang dependency dari `requirements.txt`, Chromium Playwright, dan membuat `.env` bila belum ada.

Atau manual:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Buat `.env` dari `.env.example`, lalu isi:

```env
TELEGRAM_TOKEN=isi_token_bot
ALLOWED_IDS=123456789
```

`ALLOWED_IDS` menerima ID Telegram dipisah koma. Kosong berarti semua user bisa memakai bot.

## Penggunaan command line

```bash
python bot.py --login
python bot.py --logout
python bot.py --import-zip <file.zip>
python bot.py --nomor 081234567890 --tab "Paket Kuota" --cari "Ilmupedia 22GB" --dry-run
python bot.py --nomor 081234567890 --tab "Paket Kuota" --voucher 10137
python tgbot.py
```

- `--voucher` lebih presisi; `--cari` menjadi fallback pencocokan teks.
- `--dry-run` memilih paket dan menampilkan harga tanpa submit order.
- Saat error order, screenshot disimpan ke `error.png`.

## Windows GUI

```bat
menuagenpulsa.bat
```

Atau:

```bash
python app.py
```

GUI mendukung cek login/saldo, login browser, import cookie ZIP, logout, instal Chromium, dan start/stop bot Telegram.

## Bot Telegram

Jalankan:

```bash
python tgbot.py
```

Alur: `/start` → pilih shortcut/cari paket → pilih nomor → konfirmasi → order.

Shortcut disimpan di `shortcuts.json`:

```json
[
  {"label": "Ilmupedia 22GB 7hr", "tab": "Paket Kuota", "cari": "Ilmupedia 22GB", "voucher": "10137"}
]
```

## Jadwal auto

Menu **Jadwal Auto** mendukung:

1. **Tiap hari** — `HH:MM`
2. **Sekali** — `DD/MM HH:MM` atau `DD/MM/YYYY HH:MM`
3. **Interval N hari** — `N HH:MM`, contoh `7 00:00`

Semua input dan notifikasi jadwal adalah WIB. Jadwal sekali yang terlewat saat bot mati tidak dijalankan saat startup. Jadwal sekali yang jatuh pada 23:40-00:35 WIB dibatalkan dan dihapus; jadwal harian/interval tetap ada untuk hari berikutnya.

## Server Linux

Instalasi server saat ini berada di `/root/agenpulsa` dan dijalankan oleh `agenpulsa.service`.

```bash
menuagenpulsa
menuagenpulsa status
menuagenpulsa logs 100
menuagenpulsa backup
```

Dashboard terminal menyediakan start/stop/restart bot, log, cek login/saldo, backup, dan login ulang.

Pilih **Login Isipulsa via VNC**. Menu menyalakan VNC/noVNC sementara lalu menampilkan URL `http://IP-SERVER:6080/vnc.html`. Buka URL itu dari perangkat satu jaringan, login Isipulsa, lalu tekan Enter di terminal. VNC otomatis mati dan bot Telegram start kembali.

Backup dibuat ke:

```text
/root/agenpulsa-backups/agenpulsa-YYYY-MM-DD-HHMMSS.tar.gz
```

## Flow order dan catatan

1. Browser memakai cookie di `profile/`.
2. Isi nomor HP agar situs memuat daftar paket.
3. Paket dipilih lewat `data-voucher` atau teks pencarian.
4. Order dikirim dengan jQuery AJAX (`$.post`), bukan `form.submit()` atau `page.click('#submit')`.

- Akun isipulsa wajib terverifikasi email dan nomor HP.
- Saldo deposit harus cukup.
- Sesi login dapat habis; login ulang dari `python bot.py --login` atau menu VNC server.
