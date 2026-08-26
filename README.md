# AgenPulsa

Bot otomatisasi pembelian pulsa/paket kuota dari [isipulsa.web.id](https://isipulsa.web.id/).

## Fitur

- Cari paket berdasarkan kata kunci atau ID voucher.
- Beli paket via command line, GUI Windows, atau bot Telegram.
- Shortcut paket, kontak pelanggan, dan jadwal auto harian, sekali, atau interval.
- Cek status login dan saldo deposit.
- Riwayat order + laporan harian/mingguan/bulanan dengan tracking profit (modal, omzet, profit).
- Notifikasi saldo menipis dan login habis ke Telegram (cek tiap 6 jam).
- Guard harga naik: order dibatalkan jika harga paket melebihi harga saat shortcut dibuat.
- Screenshot error order otomatis dikirim ke Telegram.
- Normalisasi nomor HP: `628777...`, `+62877...`, `62 877...`, `0821-0889...` otomatis jadi format `08...`.
- Inject cookies dari export Cookie-Editor (JSON) tanpa buka browser.
- Semua jadwal memakai zona waktu WIB (`Asia/Jakarta`).
- Transaksi manual dan auto dibatalkan pada 23:40-00:35 WIB untuk rekap situs.
- Dashboard terminal Linux: status, log, backup, login via VNC sementara (auto-stop 15 menit).

## Struktur

```
app.py                  # GUI dashboard tkinter (Windows)
bot.py                  # engine order Playwright + riwayat/laporan order
menuagenpulsa           # dashboard terminal Linux
menuagenpulsa.bat       # launcher GUI Windows
setup.py                # installer (venv, env, service, VNC)
tgbot.py                # bot Telegram
shortcuts.json          # daftar shortcut paket (termasuk harga_max, harga_jual)
contacts.json           # kontak runtime (dibuat otomatis)
schedules.json          # jadwal runtime (dibuat otomatis)
settings.json           # setting runtime: batas saldo, laporan (dibuat otomatis)
orders.json             # riwayat order (dibuat otomatis)
profile/                # profile/cookie browser setelah login
```

## Instalasi

```bash
python3 setup.py
```

Setup otomatis:

1. Membuat virtualenv `.venv/` (Linux modern menolak pip global / PEP 668).
2. Install dependency + Chromium Playwright.
3. Menanya token bot Telegram dan ID yang diizinkan, lalu menulis `.env`.
4. Linux: install VNC stack jika belum ada (ditanya dulu), pasang `menuagenpulsa` ke PATH.
5. Cek service systemd yang sudah ada (`agenpulsa`/`agenpulsaauto`) supaya tidak duplikat; enable + start otomatis jika token sudah diisi.

Atau manual:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium
```

Isi `.env`:

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
python bot.py --import-cookies <cookies.json>
python bot.py --nomor 081234567890 --tab "Paket Kuota" --cari "Ilmupedia 22GB" --dry-run
python bot.py --nomor 081234567890 --tab "Paket Kuota" --voucher 10137
python tgbot.py
```

- `--voucher` lebih presisi; `--cari` menjadi fallback pencocokan teks.
- `--dry-run` memilih paket dan menampilkan harga tanpa submit order.
- `--import-cookies` menerima export JSON dari extension Cookie-Editor (Chrome/Firefox).
- Saat error order, screenshot disimpan ke `error.png` dan dikirim ke Telegram.

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

Nomor tujuan bebas format: `628777...`, `+62877...`, `62 877...`, `0821-0889...` semua dinormalisasi ke `08...`.

Saat membuat shortcut, bot menyimpan:

- `harga_max` — harga paket saat shortcut dibuat; order dibatalkan jika harga naik melebihi ini.
- `harga_jual` — harga jual ke pelanggan untuk hitung profit (isi 0 jika pakai sendiri).

```json
[
  {"label": "Ilmupedia 22GB 7hr", "tab": "Paket Kuota", "cari": "Ilmupedia 22GB", "voucher": "10137", "harga_max": 13749, "harga_jual": 15000}
]
```

## Laporan dan profit

- Setiap order tercatat ke `orders.json` (maks 2000 entri).
- Menu Telegram **Laporan Order** → Harian / Mingguan (7 hari) / Bulanan (30 hari).
- Laporan harian otomatis dikirim tiap 21:00 WIB.
- Isi laporan: jumlah sukses/gagal, modal keluar, omzet jual, profit, daftar order terakhir.

## Notifikasi saldo

- Menu Telegram **Atur Notif Saldo Menipis** atau menu terminal opsi 9.
- Bot cek saldo tiap 6 jam; kirim peringatan jika saldo di bawah batas atau login habis.
- Notifikasi hanya sekali per kondisi, reset otomatis saat pulih.

## Jadwal auto

Menu **Jadwal Auto** mendukung:

1. **Tiap hari** — `HH:MM`
2. **Sekali** — `DD/MM HH:MM` atau `DD/MM/YYYY HH:MM`
3. **Interval N hari** — `N HH:MM`, contoh `7 00:00`

Semua input dan notifikasi jadwal adalah WIB. Jadwal sekali yang terlewat saat bot mati tidak dijalankan saat startup. Jadwal sekali yang jatuh pada 23:40-00:35 WIB dibatalkan dan dihapus; jadwal harian/interval tetap ada untuk hari berikutnya.

## Server Linux

Instalasi server berada di folder proyek dan dijalankan oleh `agenpulsa.service`.

```bash
menuagenpulsa
menuagenpulsa status
menuagenpulsa logs 100
menuagenpulsa backup
```

Menu terminal:

```
[1] Cek login dan saldo
[2] Start bot Telegram
[3] Stop bot Telegram
[4] Restart bot Telegram
[5] Lihat log bot
[6] Login Isipulsa via VNC (sementara)
[7] Backup aplikasi + cookie
[8] Inject cookies dari file JSON (Cookie-Editor)
[9] Atur batas saldo menipis (notif Telegram)
```

Pilih **Login Isipulsa via VNC**. Menu menyalakan VNC/noVNC sementara lalu menampilkan URL `http://IP-SERVER:6080/vnc.html`. Buka URL itu dari perangkat satu jaringan, login Isipulsa, lalu tekan Enter di terminal. VNC otomatis mati (atau auto-stop setelah 15 menit) dan bot Telegram start kembali.

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
- Sesi login dapat habis; login ulang dari `python bot.py --login`, inject cookies, atau menu VNC server.
