"""
uji_laporan_ekstensi.py -- menjalankan skenario Tabel 3.16 (TC-01..TC-07) + uji ketahanan pada ekstensi
yang termuat di browser sungguhan. Halaman uji = HTML nyata dari test/holdout set, disajikan pada URL
aslinya (https://<domain>.ac.id/...) lewat intersepsi jaringan sehingga content script `.ac.id` berjalan otomatis
tanpa internet.

Prasyarat: server hidup, `pip install playwright`, Chromium Playwright dan/atau Microsoft Edge terpasang.
    python tests/uji_laporan_ekstensi.py --channel chromium|msedge [--n 25] ["<folder MODELS>"]
Keluaran: docs/hasil_uji/hasil_ekstensi_<channel>.json  +  docs/hasil_uji/gambar/<channel>/*.png
"""
import argparse
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
ap = argparse.ArgumentParser()
ap.add_argument("--channel", default="chromium", choices=["chromium", "msedge"])
ap.add_argument("--n", type=int, default=25, help="halaman per kelas")
ap.add_argument("models", nargs="?", default=r"C:\Users\Andra\PycharmProjects\MODELS")
args = ap.parse_args()
MODELS = Path(args.models)
OUT = ROOT / "docs" / "hasil_uji"
IMG = OUT / "gambar" / args.channel
IMG.mkdir(parents=True, exist_ok=True)

res = {"channel": args.channel, "dibuat": time.strftime("%Y-%m-%d %H:%M:%S"), "tc": {}}
log_console = []


def pseudo_url(domain, path):
    slug = re.sub(r"_[0-9a-f]{10}$", "", Path(path).stem)
    return f"https://{domain}/{'' if slug == 'index' else slug}"


# ----------------------------------------------------------------------------- halaman uji
HIDDEN_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Jurnal Uji Tersembunyi</title></head><body>
<h1>Jurnal Ilmiah Uji</h1><p>Halaman akademik biasa tentang penelitian pendidikan dasar dan evaluasi pembelajaran di sekolah.</p>
<nav style="display:none"><a href="/a">Menu</a><a href="/b">Profil</a></nav>
<div id="t1" style="display:none">slot gacor hari ini situs slot online maxwin</div>
<div id="t2" style="visibility:hidden">togel online resmi bandar togel toto macau</div>
<div id="t3" style="opacity:0">demo slot pragmatic play rtp live bocoran slot gacor</div>
<div id="t4" style="font-size:0">situs slot gacor mahjong ways scatter hitam</div>
<div id="t5" style="position:absolute;left:-9999px;top:-9999px">agen judi online sbobet live casino</div>
</body></html>"""

NORMAL_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Beranda Program Studi</title></head><body>
<h1>Program Studi Teknik Informatika</h1><p>Penerimaan mahasiswa baru, kurikulum, seminar, dan kegiatan akademik program studi.</p>
<div style="display:none">Menu navigasi mobile: Beranda, Profil, Dosen, Kontak</div></body></html>"""

DYNAMIC_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Portal Kampus</title></head><body>
<h1>Portal Informasi Kampus</h1><p>Informasi akademik, jadwal perkuliahan, dan pengumuman resmi kampus untuk mahasiswa.</p>
<script>setTimeout(function(){var d=document.createElement('div');
d.innerHTML='<h2>SLOT GACOR HARI INI</h2><p>situs slot online maxwin terpercaya, daftar slot gacor, rtp live, bocoran slot gacor, demo slot pragmatic play, togel online resmi, bandar togel, bonus new member, deposit pulsa, wd cepat, link alternatif</p><a href="https://slot88-gacor.example.com">daftar</a>';
document.body.appendChild(d);},2500);</script></body></html>"""

BROKEN_HTML = "<html><body><div><p>Teks tanpa penutup <b>tebal <i>miring <a href='/x'>tautan<table><tr><td>sel <div>"\
              "slot gacor <span>maxwin</div></td></tr></body>" + "<p>akhir halaman rusak &amp; entitas &bogus; <" * 3
EMPTY_PAGE = "<!doctype html><html><head><title>Kosong</title></head><body></body></html>"
JSON_PAGE = '{"status":"ok","pesan":"ini bukan HTML"}'
HUGE_PAGE = "<!doctype html><html><head><meta charset='utf-8'><title>Besar</title></head><body>" + \
            "".join(f"<p>Paragraf {i} tentang kegiatan akademik universitas dan penelitian dosen. <a href='/p{i}'>baca</a></p>" for i in range(14000)) + "</body></html>"
DEEP_PAGE = "<!doctype html><html><body>" + "<div>" * 1500 + "slot gacor maxwin situs slot online" + "</div>" * 1500 + "</body></html>"

SYNTH = {
    "https://uji-hidden.ac.id/": HIDDEN_PAGE,
    "https://uji-normal.ac.id/": NORMAL_PAGE,
    "https://uji-dinamis.ac.id/": DYNAMIC_PAGE,
    "https://uji-rusak.ac.id/": BROKEN_HTML,
    "https://uji-kosong.ac.id/": EMPTY_PAGE,
    "https://uji-json.ac.id/": JSON_PAGE,
    "https://uji-besar.ac.id/": HUGE_PAGE,
    "https://uji-dalam.ac.id/": DEEP_PAGE,
}


def stat(v):
    v = sorted(v)
    if not v:
        return {}
    return {"n": len(v), "rata_rata": round(statistics.mean(v), 1), "median": round(statistics.median(v), 1),
            "p95": round(v[int(0.95 * (len(v) - 1))], 1), "min": round(min(v), 1), "maks": round(max(v), 1)}


def main():
    # ---- pilih halaman nyata dari test+holdout (belum pernah dilihat model saat training)
    df = pd.read_csv(MODELS / "training_final" / "data" / "split_train_test_holdout.csv")
    ev = df[df.split.isin(["test", "holdout"])]
    sample = pd.concat([ev[ev.label == 1].sample(args.n, random_state=7), ev[ev.label == 0].sample(args.n, random_state=7)]).reset_index(drop=True)
    pages = {}
    for _, r in sample.iterrows():
        try:
            pages[pseudo_url(r.domain, r.path_abs)] = (open(r.path_abs, encoding="utf-8").read(), int(r.label), r.path_key)
        except OSError:
            pass
    print(f"halaman nyata siap: {len(pages)}", flush=True)

    with sync_playwright() as p:
        kw = dict(headless=False, args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}",
                                        "--disable-features=DisableLoadExtensionCommandLineSwitch", "--no-first-run",
                                        "--no-default-browser-check"],
                  ignore_default_args=["--disable-extensions"])
        if args.channel == "msedge":
            kw["channel"] = "msedge"
        ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="djo-uji-"), **kw)

        def handler(route):
            u = route.request.url
            if u in pages:
                route.fulfill(status=200, headers={"content-type": "text/html; charset=utf-8"}, body=pages[u][0])
            elif u in SYNTH:
                ct = "application/json" if u.endswith("uji-json.ac.id/") else "text/html; charset=utf-8"
                route.fulfill(status=200, headers={"content-type": ct}, body=SYNTH[u])
            elif urlparse(u).hostname in ("127.0.0.1", "localhost") or u.startswith(("chrome-extension:", "data:", "about:")):
                route.continue_()
            else:
                route.abort()

        ctx.route("**/*", handler)
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=20000)
        ext_id = sw.url.split("/")[2]
        sw.on("console", lambda m: log_console.append(("sw", m.type, m.text)))

        first = ctx.new_page()
        ua = first.evaluate("navigator.userAgent")
        res["browser"] = {"user_agent": ua, "versi": re.search(r"(Edg|Chrome)/([\d.]+)", ua).group(0)}
        first.close()
        manifest = sw.evaluate("chrome.runtime.getManifest()")
        res["manifest"] = {"manifest_version": manifest["manifest_version"], "versi_ekstensi": manifest["version"],
                           "permissions": manifest["permissions"]}
        print("browser:", res["browser"]["versi"], "| MV", manifest["manifest_version"], flush=True)

        def tab_id(url):
            return sw.evaluate("async (u) => { const t = (await chrome.tabs.query({})).find(x => x.url === u); return t ? t.id : null; }", url)

        def state(tid):
            return sw.evaluate("async (k) => (await chrome.storage.session.get(k))[k] || null", f"state_{tid}")

        def badge(tid):
            return sw.evaluate("async (t) => await chrome.action.getBadgeText({tabId: t})", tid)

        def wait_done(url, timeout=30, require_new_after=None):
            t0 = time.time()
            while time.time() - t0 < timeout:
                tid = tab_id(url)
                if tid is not None:
                    s = state(tid)
                    if s and s.get("url") == url and s.get("status") in ("done", "error"):
                        if require_new_after is None or s.get("at", 0) > require_new_after:
                            return tid, s
                time.sleep(0.15)
            return tab_id(url), None

        def open_scan(url, manual=False):
            pg = ctx.new_page()
            pg.goto(url, wait_until="load")
            t_load = time.time()
            if manual:
                tid = tab_id(url)
                sw.evaluate("""async (t) => { await chrome.scripting.executeScript({target:{tabId:t}, files:['lexicon.js','scanner.js','content.js']});
                    await new Promise(r=>setTimeout(r,300)); return await chrome.tabs.sendMessage(t,{type:'RESCAN',manual:true}); }""", tid)
            tid, s = wait_done(url)
            return pg, tid, s, (time.time() - t_load) * 1000

        def popup_text(tid, shot=None):
            pop = ctx.new_page()
            pop.set_viewport_size({"width": 380, "height": 900})
            t0 = time.perf_counter()
            pop.goto(f"chrome-extension://{ext_id}/popup.html?tab={tid}")
            pop.wait_for_function("() => !document.getElementById('content').innerText.includes('Memuat')", timeout=10000)
            ms = (time.perf_counter() - t0) * 1000
            pop.wait_for_timeout(250)
            txt = pop.inner_text("#content")
            if shot:
                pop.screenshot(path=str(IMG / shot), full_page=True)
            pop.close()
            return txt, ms

        # ================= TC-01 / TC-02 / TC-06 : halaman nyata =================
        rows = []
        popup_ms = []
        for i, (url, (_, label, key)) in enumerate(pages.items(), 1):
            pg, tid, s, load_to_done = open_scan(url)
            if not s or s.get("status") != "done":
                rows.append({"url": url, "label_benar": label, "key": key, "status": (s or {}).get("status", "timeout"), "error": (s or {}).get("error")})
                pg.close(); continue
            r = s["result"]
            row = {"url": url, "label_benar": label, "key": key, "status": "done", "label_ekstensi": r["label"],
                   "p_judi": r["ml"]["p_judi"], "badge": badge(tid), "banner": pg.locator("#djo-root").count() == 1,
                   "marks": pg.locator("mark.djo-mark").count(),
                   "kw_kuat": sum(r["evidence"]["keywords_strong"].values()), "hidden": len(r["evidence"]["hidden"]),
                   "ms_ekstrak": s["timing"]["client_extract"], "ms_api": s["timing"]["api_roundtrip"],
                   "ms_e2e": s["timing"]["end_to_end"], "ms_server": r["timing_ms"]["total"], "ms_load_ke_hasil": round(load_to_done)}
            if i <= 10:
                txt, pm = popup_text(tid)
                popup_ms.append(pm)
                row["ms_popup_tampil"] = round(pm)
                row["popup_persen"] = bool(re.search(r"\d+(\.\d+)?%", txt))
            rows.append(row)
            if i in (1, args.n + 1):
                pg.screenshot(path=str(IMG / ("halaman_nyata_judi.png" if label == 1 else "halaman_nyata_normal.png")))
            pg.close()
            if i % 10 == 0:
                print(f"  halaman nyata {i}/{len(pages)}", flush=True)
        done = [r for r in rows if r["status"] == "done"]
        pd.DataFrame(rows).to_csv(OUT / f"ekstensi_halaman_nyata_{args.channel}.csv", index=False)

        def conf(lbl_pos):
            tp = sum(1 for r in done if r["label_benar"] == 1 and r["label_ekstensi"] in lbl_pos)
            fn = sum(1 for r in done if r["label_benar"] == 1 and r["label_ekstensi"] not in lbl_pos)
            fp = sum(1 for r in done if r["label_benar"] == 0 and r["label_ekstensi"] in lbl_pos)
            tn = sum(1 for r in done if r["label_benar"] == 0 and r["label_ekstensi"] not in lbl_pos)
            return {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
                    "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                    "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                    "akurasi": round((tp + tn) / len(done), 4) if done else None}

        judi = [r for r in done if r["label_benar"] == 1]
        norm = [r for r in done if r["label_benar"] == 0]
        res["tc"]["TC-01"] = {"halaman": len(judi), "terdeteksi_judi": sum(r["label_ekstensi"] == "judi" for r in judi),
                              "waspada": sum(r["label_ekstensi"] == "waspada" for r in judi),
                              "lolos_aman": sum(r["label_ekstensi"] == "aman" for r in judi),
                              "badge_tanda_seru": sum(r["badge"] == "!" for r in judi), "banner_tampil": sum(r["banner"] for r in judi),
                              "rata2_sorotan": round(statistics.mean(r["marks"] for r in judi), 1) if judi else None}
        res["tc"]["TC-02"] = {"halaman": len(norm), "aman": sum(r["label_ekstensi"] == "aman" for r in norm),
                              "waspada": sum(r["label_ekstensi"] == "waspada" for r in norm),
                              "salah_judi": sum(r["label_ekstensi"] == "judi" for r in norm),
                              "badge_ok": sum(r["badge"] == "OK" for r in norm), "banner_tidak_tampil": sum(not r["banner"] for r in norm)}
        res["konfusi_ekstensi"] = {"judi_saja_sebagai_positif": conf({"judi"}), "judi_atau_waspada_sebagai_positif": conf({"judi", "waspada"}),
                                   "halaman_gagal_dipindai": [r for r in rows if r["status"] != "done"]}
        res["tc"]["TC-06"] = {"e2e_ms": stat([r["ms_e2e"] for r in done]), "server_ms": stat([r["ms_server"] for r in done]),
                              "ekstraksi_ms": stat([r["ms_ekstrak"] for r in done]), "load_ke_hasil_ms": stat([r["ms_load_ke_hasil"] for r in done]),
                              "popup_tampil_ms": stat(popup_ms),
                              "persen_di_bawah_2000ms_e2e": round(100 * sum(r["ms_e2e"] < 2000 for r in done) / len(done), 1) if done else None,
                              "persen_di_bawah_2000ms_load_ke_hasil": round(100 * sum(r["ms_load_ke_hasil"] < 2000 for r in done) / len(done), 1) if done else None}

        # ================= TC-03 : elemen tersembunyi =================
        pg, tid, s, _ = open_scan("https://uji-hidden.ac.id/")
        r = s["result"]
        teknik = {"display:none": "display:none", "visibility:hidden": "visibility:hidden", "opacity:0": "opacity:0",
                  "font-size:0": "font-size:0", "di luar layar": "di luar layar"}
        found = {k: any(v in h["reason"] for h in r["evidence"]["hidden"]) for k, v in teknik.items()}
        res["tc"]["TC-03"] = {"blok_tersembunyi_berkata_kunci": 5, "terdeteksi": sum(found.values()), "per_teknik": found,
                              "jumlah_elemen_dilaporkan": len(r["evidence"]["hidden"]),
                              "fitur_has_hidden": r["features"]["FSTR_02_has_hidden"],
                              "label": r["label"], "p_judi": r["ml"]["p_judi"]}
        pg.screenshot(path=str(IMG / "uji_tersembunyi_halaman.png"))
        txt, _ = popup_text(tid, "uji_tersembunyi_popup.png")
        res["tc"]["TC-03"]["popup_menampilkan_elemen_tersembunyi"] = "tersembunyi" in txt.lower()
        pg.close()
        # kontrol negatif: menu tersembunyi TANPA kata kunci tidak boleh dilaporkan
        pg, tid, s, _ = open_scan("https://uji-normal.ac.id/")
        r = s["result"]
        res["tc"]["TC-03"]["kontrol_negatif"] = {"elemen_tersembunyi_dilaporkan": len(r["evidence"]["hidden"]), "has_hidden_fitur": r["features"]["FSTR_02_has_hidden"], "label": r["label"]}
        txt, _ = popup_text(tid, "uji_aman_popup.png")
        pg.screenshot(path=str(IMG / "uji_aman_halaman.png"))
        pg.close()

        # ================= TC-05 : tampilan confidence (halaman judi nyata) =================
        url_j = next(u for u, v in pages.items() if v[1] == 1)
        pg, tid, s, _ = open_scan(url_j)
        txt, _ = popup_text(tid, "popup_judi_nyata.png")
        pg.screenshot(path=str(IMG / "halaman_judi_nyata_dengan_sorotan.png"))
        m = re.search(r"(\d+(?:\.\d+)?)%", txt)
        # buka panel lencana (klik) lalu tangkap layar
        res["tc"]["TC-05"] = {"persen_tampil_di_popup": bool(m), "nilai": m.group(0) if m else None,
                              "label_tampil": any(k in txt for k in ("Terindikasi", "Aman", "Waspada")),
                              "cuplikan_popup": txt[:160].replace("\n", " | ")}
        pg.close()

        # ================= TC-04 : error koneksi =================
        sw.evaluate("async () => { const c=(await chrome.storage.local.get('settings')).settings||{}; await chrome.storage.local.set({settings:{...c, apiUrl:'http://127.0.0.1:5999'}}); }")
        pg, tid, s, _ = open_scan("https://uji-normal.ac.id/")
        alive = True
        try:
            alive = sw.evaluate("1+1") == 2
        except Exception:  # noqa: BLE001
            alive = False
        txt, _ = popup_text(tid, "uji_error_popup.png")
        res["tc"]["TC-04"] = {"status_state": (s or {}).get("status"), "pesan": (s or {}).get("error"),
                              "service_worker_hidup": alive, "halaman_tetap_berfungsi": pg.title() == "Beranda Program Studi",
                              "popup_menampilkan_pesan": ("tidak bisa" in txt.lower() or "terhubung" in txt.lower()), "cuplikan_popup": txt[:200].replace("\n", " | "),
                              "badge": badge(tid)}
        pg.close()
        sw.evaluate("async () => { const c=(await chrome.storage.local.get('settings')).settings||{}; delete c.apiUrl; await chrome.storage.local.set({settings:c}); }")

        # ================= konten dinamis (MutationObserver) =================
        url_d = "https://uji-dinamis.ac.id/"
        pg = ctx.new_page(); pg.goto(url_d, wait_until="load")
        tid, s0 = wait_done(url_d, 20)
        label_awal = s0["result"]["label"] if s0 else None
        t0 = time.time(); label_akhir = None; rescans = 0
        while time.time() - t0 < 40:
            tid = tab_id(url_d); s1 = state(tid)
            if s1 and s1.get("status") == "done" and s1["result"]["label"] != "aman":
                label_akhir = s1["result"]["label"]; rescans = s1.get("trigger"); break
            time.sleep(0.5)
        res["tc"]["KONTEN_DINAMIS"] = {"label_awal": label_awal, "label_setelah_injeksi": label_akhir, "pemicu": rescans,
                                       "waktu_deteksi_s": round(time.time() - t0, 1)}
        pg.screenshot(path=str(IMG / "uji_dinamis_halaman.png"))
        pg.close()

        # ================= ketahanan input tidak sempurna =================
        rob = {}
        for nama, url in (("html_rusak", "https://uji-rusak.ac.id/"), ("halaman_kosong", "https://uji-kosong.ac.id/"),
                          ("bukan_html_json", "https://uji-json.ac.id/"), ("halaman_besar_14000_paragraf", "https://uji-besar.ac.id/"),
                          ("dom_sangat_dalam_1500", "https://uji-dalam.ac.id/")):
            t0 = time.time()
            try:
                pg, tid, s, ms = open_scan(url)
                ok = bool(s and s.get("status") == "done")
                rob[nama] = {"berhasil": ok, "label": s["result"]["label"] if ok else None,
                             "p_judi": s["result"]["ml"]["p_judi"] if ok else None,
                             "error": (s or {}).get("error"), "ms_e2e": s["timing"]["end_to_end"] if ok else None,
                             "ms_ekstrak": s["timing"]["client_extract"] if ok else None,
                             "dom_depth": s["result"]["features"]["FSTR_03_dom_depth"] if ok else None,
                             "tautan": s["result"]["features"]["FLNK_01_link_count"] if ok else None}
                pg.close()
            except Exception as e:  # noqa: BLE001
                rob[nama] = {"berhasil": False, "pengecualian": str(e)[:200]}
        rob["service_worker_masih_hidup"] = sw.evaluate("1+1") == 2
        res["tc"]["KETAHANAN"] = rob

        # ================= TC-07 : kompatibilitas MV3 =================
        errs = []
        for nm, url in (("popup", f"chrome-extension://{ext_id}/popup.html"), ("options", f"chrome-extension://{ext_id}/options.html")):
            pg = ctx.new_page()
            pg.on("pageerror", lambda e, nm=nm: errs.append((nm, str(e))))
            pg.on("console", lambda m, nm=nm: errs.append((nm, m.text)) if m.type == "error" else None)
            pg.goto(url); pg.wait_for_timeout(700)
            if nm == "options":
                pg.click("#testBtn"); pg.wait_for_timeout(1500)
                res["tc"].setdefault("TC-07", {})["tes_koneksi_di_pengaturan"] = pg.inner_text("#srv")[:120].replace("\n", " | ")
                pg.screenshot(path=str(IMG / "pengaturan.png"), full_page=True)
            pg.close()
        sw_err = [c for c in log_console if c[1] == "error"]
        res["tc"].setdefault("TC-07", {}).update({
            "browser": res["browser"]["versi"], "manifest_version": manifest["manifest_version"], "service_worker_aktif": True,
            "galat_popup_options": errs, "galat_service_worker": sw_err,
            "jumlah_galat_total": len(errs) + len(sw_err)})

        # riwayat
        hist = sw.evaluate("async () => (await chrome.storage.local.get('history')).history || []")
        res["riwayat_tersimpan"] = len(hist)
        ctx.close()

    (OUT / f"hasil_ekstensi_{args.channel}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["tc"], indent=1)[:6000])


if __name__ == "__main__":
    main()
