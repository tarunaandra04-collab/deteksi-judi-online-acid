"""
e2e_browser.py -- uji ujung-ke-ujung: browser Chromium sungguhan + ekstensi termuat + server Flask.

Prasyarat: server jalan (jalankan.ps1 -NoBrowser), `pip install playwright` dan `playwright install chromium`.
Jalankan:  python tests/e2e_browser.py
Mengambil tangkapan layar ke tests/_hasil_e2e/ (diabaikan git).
"""
import http.server
import socketserver
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
PAGES = ROOT / "tests" / "halaman_uji"
OUT = ROOT / "tests" / "_hasil_e2e"
OUT.mkdir(exist_ok=True)
PORT = 8765

ok_all = True


def check(name, cond, extra=""):
    global ok_all
    ok_all &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))


def serve():
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(PAGES))
    handler.log_message = lambda *a, **k: None
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    srv = serve()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            tempfile.mkdtemp(prefix="djo-prof-"), headless=False,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
        )
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
        ext_id = sw.url.split("/")[2]
        print("extension id:", ext_id)

        def scan(page_name):
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/{page_name}")
            page.wait_for_load_state("load")
            # mode manual: sama seperti menekan "Pindai halaman ini" -- inject + RESCAN lewat service worker
            res = sw.evaluate(
                """async (url) => {
                    const tabs = await chrome.tabs.query({});
                    const tab = tabs.find(t => t.url && t.url.includes(url));
                    await chrome.scripting.executeScript({target:{tabId: tab.id}, files:['lexicon.js','scanner.js','content.js']});
                    await new Promise(r => setTimeout(r, 400));
                    const r = await chrome.tabs.sendMessage(tab.id, {type:'RESCAN', manual:true});
                    return {tabId: tab.id, r};
                }""", page_name)
            return page, res

        # --- normal ---
        page, res = scan("normal.html")
        r = res["r"]
        check("normal.html: pemindaian berhasil", r.get("ok"), str(r.get("error", "")))
        if r.get("ok"):
            res_ = r["result"]
            check("normal.html: label aman", res_["label"] == "aman", f"label={res_['label']} p={res_['ml']['p_judi']}")
            check("normal.html: waktu server < 2000 ms", res_["timing_ms"]["total"] < 2000, f"{res_['timing_ms']['total']} ms")
        page.screenshot(path=str(OUT / "normal.png"))

        # --- judi terang ---
        page, res = scan("judi_terang.html")
        r = res["r"]
        check("judi_terang.html: pemindaian berhasil", r.get("ok"), str(r.get("error", "")))
        if r.get("ok"):
            res_ = r["result"]
            check("judi_terang.html: label judi", res_["label"] == "judi", f"label={res_['label']} p={res_['ml']['p_judi']}")
            marks = page.locator("mark.djo-mark").count()
            check("judi_terang.html: kata kunci tersorot di halaman", marks > 5, f"{marks} sorotan")
            check("judi_terang.html: lencana tampil", page.locator("#djo-root").count() == 1)
            check("judi_terang.html: tautan judi ditandai", page.locator("a.djo-link").count() >= 1)
        page.screenshot(path=str(OUT / "judi_terang.png"))

        # --- judi tersembunyi ---
        page, res = scan("judi_tersembunyi.html")
        r = res["r"]
        check("judi_tersembunyi.html: pemindaian berhasil", r.get("ok"), str(r.get("error", "")))
        if r.get("ok"):
            res_ = r["result"]
            hid = res_["evidence"]["hidden"]
            check("judi_tersembunyi.html: elemen tersembunyi terdeteksi", len(hid) >= 1, str(hid[:1]))
            check("judi_tersembunyi.html: label bukan aman", res_["label"] in ("judi", "waspada"), f"label={res_['label']} p={res_['ml']['p_judi']}")
            check("judi_tersembunyi.html: fitur has_hidden = 1", res_["features"]["FSTR_02_has_hidden"] == 1)
            print("   alasan:", *res_["reasons"], sep="\n    - ")
        page.screenshot(path=str(OUT / "judi_tersembunyi.png"))

        # --- popup ---
        pop = ctx.new_page()
        pop.set_viewport_size({"width": 380, "height": 900})
        pop.goto(f"chrome-extension://{ext_id}/popup.html?tab={res['tabId']}")
        pop.wait_for_timeout(800)
        txt = pop.inner_text("#content")
        check("popup menampilkan hasil + alasan", "peluang konten judi" in txt.lower() and "mengapa hasilnya begini" in txt.lower())
        pop.screenshot(path=str(OUT / "popup_judi_tersembunyi.png"), full_page=True)

        # --- riwayat tersimpan ---
        hist = sw.evaluate("async () => (await chrome.storage.local.get('history')).history || []")
        check("riwayat tersimpan (3 pemindaian)", len(hist) >= 3, f"{len(hist)} entri")

        # --- server mati / galat: alamat API salah ---
        sw.evaluate("async () => { const s={apiUrl:'http://127.0.0.1:5999'}; const cur=(await chrome.storage.local.get('settings')).settings||{}; await chrome.storage.local.set({settings:{...cur,...s}}); }")
        page, res = scan("normal.html")
        r = res["r"]
        check("server tak terjangkau -> galat informatif (tanpa crash)", (not r.get("ok")) and "server" in r.get("error", "").lower(), r.get("error", ""))
        sw.evaluate("async () => { const cur=(await chrome.storage.local.get('settings')).settings||{}; delete cur.apiUrl; await chrome.storage.local.set({settings:cur}); }")

        ctx.close()
    srv.shutdown()
    print("\nHASIL:", "SEMUA LULUS" if ok_all else "ADA YANG GAGAL")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
