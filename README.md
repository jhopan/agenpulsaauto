# AgenPulsa

Bot otomatisasi pembelian pulsa/paket kuota dari [isipulsa.web.id](https://isipulsa.web.id/).

## Fitur

- **Cari paket** berdasarkan kata kunci atau ID voucher
- **Beli paket** via command line, dashboard GUI, atau bot Telegram
- **Shortcut paket** (label tombol + ID voucher presisi)
- **Simpan kontak** nomor HP customer
- **Jadwal auto** beli paket tiap hari jam tertentu (WIB)
- **GUI dashboard** (login, cek saldo, cek Telegram, instalasi Chromium)

## Struktur

```
app.py                  # GUI dashboard (tkinter)
bot.py                  # engine order (playwright)
tgbot.py                # bot Telegram (python-telegram-bot)
shortcuts.json          # daftar shortcut paket
config.json             # token bot + whitelist user
contacts.json           # kontak tersimpan (dibuat runtime)
schedules.json         # jadwal beli (dibuat runtime)
profile/                # cookies login (dibuat setelah login)
```

## Instalasi

```bash
pip install playwright "python-telegram-bot[job-queue]"
python -m playwright install chromium
```

atau klik tombol `Install Chromium` di GUI.

## Penggunaan

### Login

```bash
python bot.py --login
```

Ketik `menuagenpulsa` (via .bat file) atau `python app.py`, klik Login.

### Cari paket

```bash
python -c "from bot import search_packages; print(search_packages('Paket Kuota', 'ilmupedia'))"
```

### Beli paket

```bash
python bot.py --nomor 081234567890 --tab "Paket Kuota" --cari "Ilmupedia 22GB"
python bot.py --nomor 081234567890 --tab "Paket Kuota" --voucher 10137
```

### Shortcut paket

Edit `shortcuts.json`:

```json
[
  {"label": "Ilmupedia 22GB 7hr", "tab": "Paket Kuota", "cari": "Ilmupedia 22GB", "voucher": "10137"}
]
```

- `voucher` = ID unik paket (`data-voucher` di situs), lebih presisi
- `cari` = kata kunci fallback kalau voucher ID tidak ketemu

### Bot Telegram

```bash
python tgbot.py
```

`config.json`:

```json
{
  "token": "123456:ABC-token",
  "allowed_ids": [123456789]
}
```

- `allowed_ids` = whitelist ID Telegram (kosong = semua boleh, tidak disarankan untuk transaksi uang)
- Alur: `/start` → klik shortcut/nama paket → pilih nomor → konfirmasi → order

### Jadwal auto

Jadwal tersimpan di `schedules.json`. Bot mendukung 3 tipe jadwal (zona waktu WIB):
1. **Tiap hari**: kirim jam (format `HH:MM`)
2. **Sekali**: kirim tanggal dan jam (format `DD/MM 00:00` atau `DD/MM/YYYY 00:00`). Jadwal akan otomatis dihapus setelah jalan.
3. **Interval N Hari**: kirim jumlah hari dan jam (format `N HH:MM`, contoh `7 00:00` untuk beli tiap 7 hari jam 00:00). Sangat cocok untuk memperpanjang paket mingguan/bulanan otomatis.

Untuk melihat atau menghapus jadwal aktif, klik menu **Jadwal Auto**. Catatan: Bot harus tetap berjalan. Jika komputer mati dan jadwal "sekali" terlewat, jadwal tersebut tidak akan dieksekusi saat bot nyala kembali.

## Flow order di situs

1. Buka isipulsa.web.id (pakai cookies login di `profile/`)
2. Klik tab produk → isi nomor HP → situs load daftar paket
3. Klik paket (`data-voucher` atau teks search) → pilih saldo
4. Submit via jQuery AJAX → `.success` true (redirect history) / false (errors)

## Catatan

- Akun harus terverifikasi (email + no HP) sebelum bisa order
- Saldo harus cukup, server tolak kalau kurang
- Sesi login bisa kadaluarsa, bot deteksi dan minta re-login (`python bot.py --login`)
