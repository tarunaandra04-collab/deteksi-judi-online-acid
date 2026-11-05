"""
build_assets.py -- membuat aset extension dari sumber tunggal.

  * extension/lexicon.js  <- backend/lexicon.json  (leksikon SAMA untuk backend & extension)
  * extension/icons/*.png <- ikon perisai (tanpa dependensi, hanya stdlib)

Jalankan ulang setiap kali backend/lexicon.json berubah:
    python scripts/build_assets.py
"""
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"


def build_lexicon():
    lex = json.loads((ROOT / "backend" / "lexicon.json").read_text(encoding="utf-8"))
    payload = {k: lex[k] for k in ("keywords", "weak", "judi_name_tokens_strict")}
    js = "// DIHASILKAN OTOMATIS oleh scripts/build_assets.py dari backend/lexicon.json -- jangan diedit manual.\n"
    js += "self.DJO_LEXICON = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    (EXT / "lexicon.js").write_text(js, encoding="utf-8")
    print("lexicon.js:", len(payload["keywords"]), "kata kunci")


def _png(size, rgba_rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rgba_rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _inside_shield(x, y):
    # koordinat 0..1; perisai: bahu lebar di atas, runcing di bawah
    if y < 0.08 or y > 0.95:
        return False
    half = 0.40 if y < 0.55 else 0.40 * (0.95 - y) / 0.40
    return abs(x - 0.5) <= max(half, 0)


def _on_check(x, y):
    # tanda centang putih
    def seg(ax, ay, bx, by, w=0.055):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        px, py = ax + t * dx, ay + t * dy
        return (x - px) ** 2 + (y - py) ** 2 <= w * w
    return seg(0.32, 0.50, 0.45, 0.63) or seg(0.45, 0.63, 0.69, 0.33)


def icon(size):
    rows = []
    ss = 3  # supersampling sederhana agar tepi halus
    for j in range(size):
        row = []
        for i in range(size):
            a = r = g = b = 0
            for sj in range(ss):
                for si in range(ss):
                    x, y = (i + (si + .5) / ss) / size, (j + (sj + .5) / ss) / size
                    if _inside_shield(x, y):
                        c = (255, 255, 255) if _on_check(x, y) else (15, 118, 110)
                        r += c[0]; g += c[1]; b += c[2]; a += 255
            n = ss * ss
            cov = a / (255 * n)
            if cov > 0:
                row += [int(r / (cov * n)), int(g / (cov * n)), int(b / (cov * n)), int(255 * cov)]
            else:
                row += [0, 0, 0, 0]
        rows.append(row)
    return _png(size, rows)


def build_icons():
    (EXT / "icons").mkdir(parents=True, exist_ok=True)
    for s in (16, 32, 48, 128):
        (EXT / "icons" / f"icon{s}.png").write_bytes(icon(s))
    print("ikon: 16/32/48/128")


if __name__ == "__main__":
    build_lexicon()
    build_icons()
