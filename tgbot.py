import asyncio
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import run_order

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ALLOWED_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_IDS", "").split(",") if x.strip().isdigit()]

SHORTCUTS = []
if os.path.exists(os.path.join(HERE, "shortcuts.json")):
    SHORTCUTS = json.load(open(os.path.join(HERE, "shortcuts.json"), encoding="utf-8"))
TZ = ZoneInfo("Asia/Jakarta")

CONTACTS_FILE = os.path.join(HERE, "contacts.json")
SCHEDULES_FILE = os.path.join(HERE, "schedules.json")

contacts = json.load(open(CONTACTS_FILE, encoding="utf-8")) if os.path.exists(CONTACTS_FILE) else {}
schedules = json.load(open(SCHEDULES_FILE, encoding="utf-8")) if os.path.exists(SCHEDULES_FILE) else []

pending = {}

NOMOR_RE = re.compile(r"^(08|\+62|62)\d{8,13}$")
JAM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
TANGGAL_JAM_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2}|\d{4}))?\s+([01]?\d|2[0-3]):([0-5]\d)$")
INTERVAL_RE = re.compile(r"^(\d{1,2})\s+([01]?\d|2[0-3]):([0-5]\d)$")
TANGGAL_JAM_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{1,2}|(\d{4}))\s+([01]?\d|2[0-3]):([0-5]\d)$")
INTERVAL_RE = re.compile(r"^(\d{1,2})\s+([01]?\d|2[0-3]):([0-5]\d)$")


def save_contacts():
    json.dump(contacts, open(CONTACTS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def save_schedules():
    json.dump(schedules, open(SCHEDULES_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def allowed(update: Update) -> bool:
    return not ALLOWED_IDS or update.effective_user.id in ALLOWED_IDS


def menu_kb():
    rows = []
    for i, sc in enumerate(SHORTCUTS):
        rows.append([InlineKeyboardButton(sc["label"], callback_data=f"sc:{i}")])
    rows.append([InlineKeyboardButton("Cari Paket Lain", callback_data="cari")])
    rows.append([InlineKeyboardButton("Jadwal Auto", callback_data="jadwal"), InlineKeyboardButton("Kontak", callback_data="kontak")])
    return InlineKeyboardMarkup(rows)


def confirm_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Ya, Beli", callback_data="ya"), InlineKeyboardButton("Batal", callback_data="batal")]]
    )


def jadwal_tipe_kb():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Tiap Hari (jam)", callback_data="tipe:harian")],
            [InlineKeyboardButton("Sekali (tanggal+j jam)", callback_data="tipe:sekali")],
            [InlineKeyboardButton("Tiap N Hari", callback_data="tipe:interval")],
        ]
    )


def contact_kb(prefix):
    rows = [[InlineKeyboardButton(n, callback_data=f"{prefix}:{n}")] for n in contacts]
    rows.append([InlineKeyboardButton("Ketik manual", callback_data=f"{prefix}:__manual__")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text("Halo! Mau beli apa?", reply_markup=menu_kb())


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    q = update.callback_query
    uid = update.effective_user.id
    data = q.data

    if data.startswith("sc:"):
        sc = SHORTCUTS[int(data.split(":")[1])]
        pending[uid] = {"tab": sc["tab"], "cari": sc["cari"], "voucher": sc.get("voucher"), "label": sc["label"]}
        await q.answer()
        if contacts:
            await q.edit_message_text(f"Paket: {sc['label']}\nPilih nomor tujuan:", reply_markup=contact_kb("nomor"))
        else:
            await q.edit_message_text(f"Paket: {sc['label']}\nKirim nomor HP tujuan (contoh 081234567890):")

    elif data == "cari":
        pending[uid] = {"cari_mode": True}
        await q.answer()
        await q.edit_message_text("Ketik kata kunci paket (contoh: Ilmupedia 22GB):")

    elif data.startswith("nomor:"):
        nama = data.split(":", 1)[1]
        job = pending.get(uid)
        if not job:
            await q.answer("Tidak ada order aktif")
            return
        if nama == "__manual__":
            job["tunggu_nomor"] = True
            await q.answer()
            await q.edit_message_text("Kirim nomor HP tujuan (contoh 081234567890):")
        else:
            job["nomor"] = contacts[nama]
            job["kontak"] = nama
            await q.answer()
            await q.edit_message_text(
                f"Konfirmasi pembelian:\nPaket: {job.get('label', job['cari'])}\nNomor: {nama} ({job['nomor']})\n\nLanjut beli?",
                reply_markup=confirm_kb(),
            )

    elif data == "ya":
        job = pending.get(uid)
        if not job or "nomor" not in job:
            await q.answer("Tidak ada order aktif")
            return
        await q.answer()
        await q.edit_message_text("Memproses order, tunggu...")
        result = await asyncio.to_thread(run_order, job["nomor"], job["tab"], cari=job.get("cari"), voucher=job.get("voucher"))
        pending.pop(uid, None)
        await ctx.bot.send_message(uid, result)

    elif data == "batal":
        pending.pop(uid, None)
        await q.answer("Dibatalkan")
        await q.edit_message_text("Dibatalkan. Mau beli apa lagi?", reply_markup=menu_kb())

    elif data == "kontak":
        pending[uid] = {"mode": "kontak_nama"}
        await q.answer()
        daftar = "\n".join(f"- {n}: {nomor}" for n, nomor in contacts.items()) or "(kosong)"
        await q.edit_message_text(f"Kontak tersimpan:\n{daftar}\n\nKirim nama kontak baru untuk tambah:")

    elif data == "jadwal":
        await q.answer()
        rows = [[InlineKeyboardButton("Tambah Jadwal", callback_data="jadwal_baru")]]
        for i, s in enumerate(schedules):
            rows.append([InlineKeyboardButton(f"Hapus: {s['label']} {s['jam']}", callback_data=f"del:{i}")])
        daftar = "\n".join(f"- {s['label']} | {s['nomor']} | {s['jam']} WIB ({s.get('tipe', 'harian')})" for s in schedules) or "(kosong)"
        await q.edit_message_text(f"Jadwal auto (tiap hari, WIT):\n{daftar}", reply_markup=InlineKeyboardMarkup(rows))

    elif data == "jadwal_baru":
        pending[uid] = {"mode": "jadwal_paket"}
        await q.answer()
        rows = [[InlineKeyboardButton(sc["label"], callback_data=f"js:{i}")] for i, sc in enumerate(SHORTCUTS)]
        await q.edit_message_text("Jadwal auto beli. Pilih paket:", reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("js:"):
        sc = SHORTCUTS[int(data.split(":")[1])]
        job = {"mode": "jadwal_kontak", "tab": sc["tab"], "cari": sc["cari"], "voucher": sc.get("voucher"), "label": sc["label"]}
        pending[uid] = job
        await q.answer()
        if contacts:
            await q.edit_message_text(f"Paket: {sc['label']}\nPilih nomor tujuan:", reply_markup=contact_kb("jkontak"))
        else:
            job["tunggu_nomor"] = True
            await q.edit_message_text(f"Paket: {sc['label']}\nKirim nomor HP tujuan:")

    elif data.startswith("jkontak:"):
        nama = data.split(":", 1)[1]
        job = pending.get(uid)
        if not job:
            await q.answer("Tidak ada proses aktif")
            return
        if nama == "__manual__":
            job["tunggu_nomor"] = True
            await q.answer()
            await q.edit_message_text("Kirim nomor HP tujuan:")
        else:
            job["nomor"] = contacts[nama]
            job["mode"] = "jadwal_tipe"
            await q.answer()
            await q.edit_message_text("Pilih tipe jadwal:", reply_markup=jadwal_tipe_kb())

    elif data.startswith("tipe:"):
        tipe = data.split(":", 1)[1]
        job = pending.get(uid)
        if not job:
            await q.answer("Tidak ada proses aktif")
            return
        job["tipe"] = tipe
        if tipe == "harian":
            job["mode"] = "jadwal_harian"
            await q.answer()
            await q.edit_message_text("Kirim jam beli tiap hari, format HH:MM (WIB). Contoh: 07:30")
        elif tipe == "sekali":
            job["mode"] = "jadwal_sekali"
            await q.answer()
            await q.edit_message_text("Kirim tanggal + jam, format DD/MM/[YYYY] HH:MM (WIB). Contoh: 22/08 00:00\n(Tahun opsional, default tahun ini)")
        elif tipe == "interval":
            job["mode"] = "jadwal_interval"
            await q.answer()
            await q.edit_message_text("Kirim format: [jumlah hari N] [jam HH:MM] (WIB). Contoh: `7 00:00` berarti beli tiap 7 hari jam 00:00 WIB.")

    elif data.startswith("del:"):
        idx = int(data.split(":")[1])
        if idx < len(schedules):
            removed = schedules.pop(idx)
            save_schedules()
            for job in ctx.job_queue.get_jobs_by_name(f"sched-{removed['id']}"):
                job.schedule_removal()
            await q.answer("Dihapus")
            await q.edit_message_text(f"Jadwal '{removed['label']}' dihapus.", reply_markup=menu_kb())
        else:
            await q.answer("Tidak ditemukan")


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    uid = update.effective_user.id
    text = update.message.text.strip()
    job = pending.get(uid)
    if not job:
        await update.message.reply_text("Klik /start untuk mulai.")
        return

    mode = job.get("mode")

    if mode == "kontak_nama":
        nama = text
        job["kontak_nama"] = nama
        job["mode"] = "kontak_nomor"
        await update.message.reply_text(f"Kontak '{nama}'. Kirim nomor HP-nya:")
        return

    if mode == "kontak_nomor":
        nomor = text.replace("-", "").replace(" ", "")
        if not NOMOR_RE.match(nomor):
            await update.message.reply_text("Nomor tidak valid. Format 08xxxxxxxxxx:")
            return
        contacts[job["kontak_nama"]] = nomor
        save_contacts()
        pending.pop(uid, None)
        await update.message.reply_text(f"Kontak '{job['kontak_nama']}' ({nomor}) tersimpan.", reply_markup=menu_kb())
        return

    if job.get("cari_mode"):
        job["cari"] = text
        job["label"] = text
        job["tab"] = "Paket Kuota"
        del job["cari_mode"]
        if contacts:
            await update.message.reply_text("Pilih nomor tujuan:", reply_markup=contact_kb("nomor"))
        else:
            job["tunggu_nomor"] = True
            await update.message.reply_text("Kirim nomor HP tujuan (contoh 081234567890):")
        return

    if job.get("tunggu_nomor"):
        nomor = text.replace("-", "").replace(" ", "")
        if not NOMOR_RE.match(nomor):
            await update.message.reply_text("Nomor tidak valid. Format 08xxxxxxxxxx:")
            return
        job["nomor"] = nomor
        del job["tunggu_nomor"]
        if mode == "jadwal_kontak":
            job["mode"] = "jadwal_jam"
            await update.message.reply_text("Kirim jam beli tiap hari, format HH:MM (WIT). Contoh: 07:30")
        else:
            await update.message.reply_text(
                f"Konfirmasi pembelian:\nPaket: {job.get('label', job['cari'])}\nNomor: {nomor}\n\nLanjut beli?",
                reply_markup=confirm_kb(),
            )
        return

    if mode == "jadwal_harian":
        m = JAM_RE.match(text)
        if not m:
            await update.message.reply_text("Format salah. Contoh: 07:30")
            return
        jam, menit = int(m.group(1)), int(m.group(2))
        sched = {
            "id": datetime.now(TZ).strftime("%Y%m%d%H%M%S"),
            "tipe": "harian",
            "label": job["label"],
            "tab": job["tab"],
            "cari": job["cari"],
            "voucher": job.get("voucher"),
            "nomor": job["nomor"],
            "jam": f"{jam:02d}:{menit:02d}",
            "chat_id": uid,
        }
        schedules.append(sched)
        save_schedules()
        ctx.job_queue.run_daily(
            scheduled_order,
            time=datetime(2000, 1, 1, jam, menit, tzinfo=TZ),
            name=f"sched-{sched['id']}",
            data=sched,
        )
        pending.pop(uid, None)
        await update.message.reply_text(
            f"Jadwal tersimpan:\nPaket: {sched['label']}\nNomor: {sched['nomor']}\nJam: {sched['jam']} WIB (tiap hari)",
            reply_markup=menu_kb(),
        )
        return

    if mode == "jadwal_sekali":
        m = TANGGAL_JAM_RE.match(text)
        if not m:
            await update.message.reply_text("Format salah. Contoh: 22/08 00:00")
            return
        hari, bln = int(m.group(1)), int(m.group(2))
        thn_str = m.group(3)
        jam, menit = int(m.group(4)), int(m.group(5))
        now = datetime.now(TZ)
        if thn_str:
            thn = int(thn_str)
            if len(thn_str) == 2:
                thn += 2000
        else:
            thn = now.year
            from datetime import datetime as _dt
            if _dt(thn, bln, hari, jam, menit, tzinfo=TZ) <= now:
                thn += 1
        from datetime import datetime as _dt
        try:
            run_at = _dt(thn, bln, hari, jam, menit, tzinfo=TZ)
        except ValueError:
            await update.message.reply_text("Tanggal tidak valid.")
            return
        if run_at <= _dt.now(TZ):
            await update.message.reply_text("Waktu sudah lewat. Kirim waktu yang akan datang.")
            return
        sched = {
            "id": datetime.now(TZ).strftime("%Y%m%d%H%M%S"),
            "tipe": "sekali",
            "label": job["label"],
            "tab": job["tab"],
            "cari": job["cari"],
            "voucher": job.get("voucher"),
            "nomor": job["nomor"],
            "jam": run_at.strftime("%d/%m/%Y %H:%M"),
            "chat_id": uid,
        }
        schedules.append(sched)
        save_schedules()
        ctx.job_queue.run_once(
            scheduled_order,
            when=run_at,
            name=f"sched-{sched['id']}",
            data=sched,
        )
        pending.pop(uid, None)
        await update.message.reply_text(
            f"Jadwal sekali tersimpan:\nPaket: {sched['label']}\nNomor: {sched['nomor']}\nWaktu: {sched['jam']} WIB",
            reply_markup=menu_kb(),
        )
        return

    if mode == "jadwal_interval":
        m = INTERVAL_RE.match(text)
        if not m:
            await update.message.reply_text("Format salah. Contoh: `7 00:00`")
            return
        n_hari, jam, menit = int(m.group(1)), int(m.group(2)), int(m.group(3))
        sched = {
            "id": datetime.now(TZ).strftime("%Y%m%d%H%M%S"),
            "tipe": "interval",
            "label": job["label"],
            "tab": job["tab"],
            "cari": job["cari"],
            "voucher": job.get("voucher"),
            "nomor": job["nomor"],
            "jam": f"{jam:02d}:{menit:02d}",
            "interval_hari": n_hari,
            "terakhir_jalan": None,
            "chat_id": uid,
        }
        schedules.append(sched)
        save_schedules()
        ctx.job_queue.run_daily(
            scheduled_order,
            time=datetime(2000, 1, 1, jam, menit, tzinfo=TZ),
            name=f"sched-{sched['id']}",
            data=sched,
        )
        pending.pop(uid, None)
        await update.message.reply_text(
            f"Jadwal interval tersimpan:\nPaket: {sched['label']}\nNomor: {sched['nomor']}\njam {sched['jam']} WIB, tiap {n_hari} hari",
            reply_markup=menu_kb(),
        )
        return

    if "cari" in job and "nomor" not in job:
        nomor = text.replace("-", "").replace(" ", "")
        if not NOMOR_RE.match(nomor):
            await update.message.reply_text("Nomor tidak valid. Kirim nomor format 08xxxxxxxxxx:")
            return
        job["nomor"] = nomor
        await update.message.reply_text(
            f"Konfirmasi pembelian:\nPaket: {job.get('label', job['cari'])}\nNomor: {nomor}\n\nLanjut beli?",
            reply_markup=confirm_kb(),
        )


async def scheduled_order(ctx: ContextTypes.DEFAULT_TYPE):
    sched = ctx.job.data
    tipe = sched.get("tipe", "harian")
    
    if tipe == "interval":
        sekarang = datetime.now(TZ)
        terakhir = sched.get("terakhir_jalan")
        if terakhir:
            try:
                dt_terakhir = datetime.strptime(terakhir, "%Y%m%d").date()
                delta = (sekarang.date() - dt_terakhir).days
                if delta < sched["interval_hari"]:
                    return
            except Exception:
                pass
        sched["terakhir_jalan"] = sekarang.strftime("%Y%m%d")
        save_schedules()
    
    result = await asyncio.to_thread(run_order, sched["nomor"], sched["tab"], cari=sched.get("cari"), voucher=sched.get("voucher"))
    await ctx.bot.send_message(sched["chat_id"], f"[JADWAL {sched['jam']} WIB] {sched['label']}\n{result}")

    if tipe == "sekali":
        for i, s in enumerate(schedules):
            if s["id"] == sched["id"]:
                schedules.pop(i)
                save_schedules()
                break


def load_schedules(app: Application):
    for sched in schedules:
        tipe = sched.get("tipe", "harian")
        if tipe in ("harian", "interval"):
            jam, menit = map(int, sched["jam"].split(":"))
            app.job_queue.run_daily(
                scheduled_order,
                time=datetime(2000, 1, 1, jam, menit, tzinfo=TZ),
                name=f"sched-{sched['id']}",
                data=sched,
            )
        elif tipe == "sekali":
            try:
                run_at = datetime.strptime(sched["jam"], "%d/%m/%Y %H:%M").replace(tzinfo=TZ)
                if run_at > datetime.now(TZ):
                    app.job_queue.run_once(
                        scheduled_order,
                        when=run_at,
                        name=f"sched-{sched['id']}",
                        data=sched,
                    )
                else:
                    # Sudah lewat waktu saat bot mati, abaikan/hapus
                    pass
            except Exception:
                pass


def main():
    if not TOKEN or "ISI_TOKEN" in TOKEN:
        print("Error: TELEGRAM_TOKEN belum diatur di .env")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    load_schedules(app)
    print(f"Bot jalan. Waktu sekarang WIT: {datetime.now(TZ):%H:%M}. Ctrl+C untuk stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
