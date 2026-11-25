"""
ambil_gambar_panel.py -- mengambil tangkapan layar halaman uji tersembunyi dengan panel lencana TERBUKA (untuk Gambar 4.13 skripsi).
Prasyarat: server hidup (jalankan.ps1 -NoBrowser), playwright + Microsoft Edge.
    python tests/ambil_gambar_panel.py
Keluaran: docs/hasil_uji/gambar/msedge/uji_tersembunyi_panel.png
"""
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
sys.argv = [sys.argv[0], "--channel", "msedge"]
src = (ROOT / "tests" / "uji_laporan_ekstensi.py").read_text(encoding="utf-8")
HIDDEN_PAGE = re.search(r'HIDDEN_PAGE = """(.*?)"""', src, re.S).group(1)
OUT = ROOT / "docs" / "hasil_uji" / "gambar" / "msedge" / "uji_tersembunyi_panel.png"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        tempfile.mkdtemp(prefix="djo-panel-"), headless=False, channel="msedge", viewport={"width": 1280, "height": 720},
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}",
              "--disable-features=DisableLoadExtensionCommandLineSwitch", "--no-first-run", "--no-default-browser-check"],
        ignore_default_args=["--disable-extensions"])

    def handler(route):
        u = route.request.url
        if u == "https://uji-hidden.ac.id/":
            route.fulfill(status=200, headers={"content-type": "text/html; charset=utf-8"}, body=HIDDEN_PAGE)
        elif urlparse(u).hostname in ("127.0.0.1", "localhost") or u.startswith(("chrome-extension:", "data:", "about:")):
            route.continue_()
        else:
            route.abort()

    ctx.route("**/*", handler)
    ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=20000)
    pg = ctx.new_page()
    pg.goto("https://uji-hidden.ac.id/")
    pg.wait_for_timeout(3500)
    pg.mouse.click(1240, 680)      # lencana bulat di pojok kanan bawah (shadow DOM tertutup -> klik koordinat)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT))
    print("tersimpan:", OUT)
    ctx.close()
