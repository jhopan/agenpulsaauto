# AgenPulsa

Proyek bot otomatisasi pembelian pulsa/paket kuota dari isipulsa.web.id.

## setup dan konfigurasi

```bash
python setup.py                          # install requirements, Chromium, buat .env bila belum ada
python -m pip install -r requirements.txt
python -m playwright install chromium
```

- Salin isi `.env.example` ke `.env`; isi `TELEGRAM_TOKEN`. `ALLOWED_IDS` menerima ID Telegram dipisah koma; kosong berarti semua user diizinkan.
- Tidak ada test, linter, atau CI config di repo saat ini.

## Perintah umum

```bash
python bot.py --login                    # login manual (cookies tersimpan di profile/)
python bot.py --logout                   # hapus sesi untuk ganti akun
python bot.py --import-zip <file.zip>    # impor folder profile/cookies dari zip
python bot.py --nomor <nohp> --cari "<kata kunci>" --dry-run   # cek paket tanpa order
python bot.py --nomor <nohp> --cari "<kata kunci>"          # order beneran
python bot.py --nomor <nohp> --tab "Paket Kuota" --voucher <id> --dry-run
python tgbot.py                          # bot Telegram jalan
python app.py                            # GUI dashboard jalan
python -m playwright install chromium     # instal browser (jika gagal)
```

## file penting

- `bot.py` — engine order, berisi `run_order()`, `search_packages()`, dan `cek_status()`
- `tgbot.py` — bot Telegram, alur menu via callback query
- `app.py` — GUI tkinter, dashboard status saldo/login
- `shortcuts.json` — shortcut paket yang dibaca dan ditulis `tgbot.py`; file ter-track.
- `contacts.json` dan `schedules.json` — data runtime bot, diabaikan Git.

## hal penting

- akses situs pakai cookies login di folder `profile/`
- submit order via jQuery AJAX (`$.post`), bukan `form.submit()` — tombol `name="submit"` shadow `form.submit()`, dan `page.click('#submit')` tidak trigger handler-nya
- `page.url` property, bukan `page.url()`
- selektor paket: `#nominal .row button` dengan atribut `data-voucher`, `data-operator`, `data-nominal`, `data-harga`
- `--voucher` dicoba lebih dulu; `--cari` menjadi fallback pencocokan teks case-insensitive.
- `--dry-run` berhenti setelah paket dan saldo dipilih, sebelum AJAX order.
- error order menyimpan screenshot `error.png`; file ini diabaikan Git.
- akun isipulsa wajib terverifikasi (email + no HP) sebelum order
- GUI `app.py` cuma Windows (launcher `menuagenpulsa.bat`); `tgbot.py`/`bot.py` cross-platform

## waktu

- `tgbot.py` pakai `TZ = ZoneInfo("Asia/Jakarta")` (WIB)
- Jadwal sekali yang telah lewat saat bot mati tidak dieksekusi saat startup.

## dependencies

- `playwright==1.57.0` (chromium)
- `python-telegram-bot[job-queue]==22.5` (APScheduler)
- `python-dotenv==1.0.1`

## todo

- porting Telegram bot webhook jika di-deploy ke server serverless (opsional, saat ini pakai long polling `run_polling()`)
