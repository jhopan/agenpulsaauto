# AgenPulsa

Proyek bot otomatisasi pembelian pulsa/paket kuota dari isipulsa.web.id.

## Perintah umum

```bash
python bot.py --login                    # login manual (cookies tersimpan di profile/)
python bot.py --nomor <nohp> --cari "<kata kunci>" --dry-run   # cek paket tanpa order
python bot.py --nomor <nohp> --cari "<kata kunci>"          # order beneran
python bot.py --nomor <nohp> --tab "Paket Kuota" --voucher <id> --dry-run
python tgbot.py                          # bot Telegram jalan
python app.py                            # GUI dashboard jalan
python -m playwright install chromium     # instal browser (jika gagal)
```

## file penting

- `bot.py` — engine order, berisi `run_order()` dan `search_packages()`
- `tgbot.py` — bot Telegram, alur menu via callback query
- `app.py` — GUI tkinter, dashboard status saldo/login

## hal penting

- akses situs pakai cookies login di folder `profile/`
- submit order via jQuery AJAX (`$.post`), bukan `form.submit()` — tombol `name="submit"` shadow `form.submit()`, dan `page.click('#submit')` tidak trigger handler-nya
- `page.url` property, bukan `page.url()`
- selektor paket: `#nominal .row button` dengan atribut `data-voucher`, `data-operator`, `data-nominal`, `data-harga`
- akun isipulsa wajib terverifikasi (email + no HP) sebelum order
- GUI `app.py` cuma Windows (launcher `.bat`); `tgbot.py`/`bot.py` cross-platform

## waktu

- `tgbot.py` pakai `TZ = ZoneInfo("Asia/Jakarta")` (WIB)

## dependencies

- `playwright` (chromium)
- `python-telegram-bot[job-queue]` (APScheduler)

## todo

- porting Telegram bot webhook jika di-deploy ke server serverless (opsional, saat ini pakai long polling `run_polling()`)
