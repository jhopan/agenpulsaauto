import argparse
import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

BASE = "https://isipulsa.web.id/"
HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, "profile")
TZ = ZoneInfo("Asia/Jakarta")
MAINTENANCE_START = time(23, 40)
MAINTENANCE_END = time(0, 35)


def is_maintenance(now=None):
    now = now or datetime.now(TZ)
    current = now.astimezone(TZ).time().replace(tzinfo=None)
    return current >= MAINTENANCE_START or current < MAINTENANCE_END


def maintenance_message():
    return "ORDER DIBATALKAN: transaksi ditutup untuk rekap dan pembukuan pukul 23:40-00:35 WIB. Silakan ulangi setelah 00:35 WIB."


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
        except Exception:
            return False, "Error"
        finally:
            ctx.close()


def search_packages(tab, keyword, nomor="081234567890"):
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=True, viewport={"width": 1366, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
            page.locator(".form-tabs a", has_text=tab).first.click()
            page.fill('input[name="nomor_hp"]', nomor)
            page.locator('input[name="nomor_hp"]').blur()
            page.wait_for_selector("#nominal .row button", state="attached", timeout=30000)
            results = page.evaluate(
                """(kw) => Array.from(document.querySelectorAll('#nominal .row button'))
                    .filter(b => b.innerText.toLowerCase().includes(kw.toLowerCase()))
                    .map(b => ({
                        voucher: b.getAttribute('data-voucher'),
                        operator: b.getAttribute('data-operator'),
                        nama: b.getAttribute('data-nominal'),
                        harga: b.getAttribute('data-harga'),
                        teks: b.innerText.replace(/\\n/g, ' ').trim()
                    }))""",
                keyword,
            )
            return results
        finally:
            ctx.close()


def run_order(nomor, tab, cari=None, voucher=None, dry_run=False, headed=False):
    if is_maintenance():
        return maintenance_message()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE,
            headless=not headed,
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(BASE, wait_until="domcontentloaded", timeout=60000)

            if page.locator("#header-signin", has_text="Masuk").count() > 0:
                return "GAGAL: sesi login habis. Jalankan: python bot.py --login"

            page.locator(".form-tabs a", has_text=tab).first.click()
            page.fill('input[name="nomor_hp"]', nomor)
            page.locator('input[name="nomor_hp"]').blur()

            page.wait_for_selector("#nominal .row button", state="attached", timeout=30000)
            page.locator("#nominal").wait_for(state="visible", timeout=10000)

            target = None
            if voucher:
                target = page.locator(f'#nominal .row button[data-voucher="{voucher}"]')
                if target.count() == 0:
                    target = None
            if target is None and cari:
                items = page.locator("#nominal .row button")
                for i in range(items.count()):
                    el = items.nth(i)
                    if cari.lower() in (el.inner_text() or "").lower():
                        target = el
                        break
            if target is None:
                return f"GAGAL: paket tidak ditemukan di tab {tab} (voucher={voucher}, cari={cari})"

            target.click()
            page.select_option("#pilihpembayaran", "balance")
            nama_paket = " ".join((target.inner_text() or "").split())
            harga = page.inner_text("#harga h3")

            if dry_run:
                return f"DRY RUN OK. Paket: {nama_paket} | Harga: {harga}"

            result = page.evaluate(
                """() => new Promise((resolve) => {
                    var url = "https://isipulsa.web.id/" + jQuery('input[name="produk"]').val();
                    jQuery.post(url, jQuery("#order_form").serialize(), function (data) {
                        resolve(JSON.stringify(data));
                    }).fail(function (xhr) {
                        resolve(JSON.stringify({success: false, errors: ["HTTP " + xhr.status]}));
                    });
                })"""
            )
            data = json.loads(result)
            if data.get("success"):
                return f"ORDER SUKSES. Paket: {nama_paket} | Harga: {harga} | ID: {data.get('id')} | https://isipulsa.web.id/history/view/{data.get('id')}"
            errors = "; ".join(data.get("errors", ["tidak diketahui"]))
            return f"ORDER GAGAL. Paket: {nama_paket} | Harga: {harga} | Alasan: {errors}"
        except Exception as e:
            try:
                page.screenshot(path=os.path.join(HERE, "error.png"), full_page=True)
            except Exception:
                pass
            return f"ERROR: {e}"
        finally:
            ctx.close()


def import_cookies(filepath):
    """Inject cookies dari export Cookie-Editor (JSON array) ke profile Playwright."""
    with open(filepath, encoding="utf-8") as f:
        raw = json.load(f)
    cookies = []
    for c in raw:
        if not c.get("name") or "value" not in c:
            continue
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".isipulsa.web.id"),
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
        }
        exp = c.get("expirationDate")
        if exp:
            entry["expires"] = int(exp)
        ss = str(c.get("sameSite", "")).lower()
        entry["sameSite"] = {"strict": "Strict", "lax": "Lax", "no_restriction": "None"}.get(ss, "Lax")
        cookies.append(entry)
    if not cookies:
        return "GAGAL: tidak ada cookie valid di file."
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=True, viewport={"width": 1366, "height": 900})
        try:
            ctx.add_cookies(cookies)
        finally:
            ctx.close()
    return f"OK: {len(cookies)} cookie diinject ke profile/. Cek dengan: python bot.py --nomor 0812 --cari test --dry-run"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="buka browser untuk login manual, cookies tersimpan di folder profile")
    ap.add_argument("--logout", action="store_true", help="hapus sesi login (untuk ganti akun)")
    ap.add_argument("--import-zip", help="import folder profile/cookies dari file zip")
    ap.add_argument("--import-cookies", help="inject cookies dari export Cookie-Editor (JSON) ke profile")
    ap.add_argument("--nomor", help="nomor HP tujuan")
    ap.add_argument("--tab", default="Paket Kuota", help="nama tab produk, misal: Pulsa, Paket Kuota, Paket Internet")
    ap.add_argument("--cari", help="kata kunci paket untuk dicari (ctrl+f style)")
    ap.add_argument("--voucher", help="ID voucher paket (lebih presisi dari --cari)")
    ap.add_argument("--dry-run", action="store_true", help="berhenti sebelum klik Order Sekarang")
    ap.add_argument("--headed", action="store_true", help="tampilkan browser")
    args = ap.parse_args()

    if args.logout:
        import shutil
        if os.path.exists(PROFILE):
            shutil.rmtree(PROFILE, ignore_errors=True)
            print("Sesi login (folder profile) berhasil dihapus. Silakan login kembali.")
        else:
            print("Tidak ada sesi login (folder profile tidak ditemukan).")
        return

    if args.import_zip:
        import zipfile
        import shutil
        filepath = args.import_zip
        if not os.path.isfile(filepath):
            print(f"Error: file '{filepath}' tidak ditemukan.")
            return
        try:
            if os.path.exists(PROFILE):
                shutil.rmtree(PROFILE, ignore_errors=True)
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(PROFILE)
            print("Berhasil mengimpor cookies dari file zip.")
        except Exception as e:
            print(f"Error saat impor zip: {e}")
        return

    if args.import_cookies:
        filepath = args.import_cookies
        if not os.path.isfile(filepath):
            print(f"Error: file '{filepath}' tidak ditemukan.")
            return
        try:
            print(import_cookies(filepath))
        except Exception as e:
            print(f"Error saat inject cookies: {e}")
        return

    if args.login:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(PROFILE, headless=False, viewport={"width": 1366, "height": 900})
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
            print("Login manual di browser. Kembali ke terminal dan tekan Enter kalau sudah.")
            input()
            ctx.close()
        return

    print(run_order(args.nomor, args.tab, cari=args.cari, voucher=args.voucher, dry_run=args.dry_run, headed=args.headed))


if __name__ == "__main__":
    main()
