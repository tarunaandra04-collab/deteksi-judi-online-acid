"""
revisi_bab45.py -- menyusun ulang Bab IV (Implementasi dan Pembahasan) dan Bab V (Penutup) pada berkas skripsi.
Bab I-III dan bagian lain TIDAK diubah. Cuplikan kode ditempatkan dalam KOTAK TEKS (bukan tabel), sesuai arahan
pembimbing pada rekaman bimbingan; gambar yang dapat dibuat otomatis dimasukkan langsung.

    python scripts/revisi_bab45.py "<SKRIPSIANDRA.docx sumber>" "<keluaran.docx>"
Butuh: python-docx, lxml.
"""
import copy
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import docx
from docx.shared import Cm
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skripsi_isi as C  # noqa: E402

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
NSDECL = (f'xmlns:w="{W}" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')

doc = docx.Document(str(SRC))
body = doc.element.body

# ------------------------------------------------------------------------------------------------ cari jangkar
def ptext(el):
    return "".join(t.text or "" for t in el.iter(f"{{{W}}}t"))


def pstyle(el):
    s = el.find("w:pPr/w:pStyle", NS)
    return s.get(f"{{{W}}}val") if s is not None else None


kids = list(body)
i4 = next(i for i, e in enumerate(kids) if e.tag == f"{{{W}}}p" and pstyle(e) == "Heading1" and ptext(e).strip() == "IMPLEMENTASI DAN PEMBAHASAN")
i5 = next(i for i, e in enumerate(kids) if i > i4 and e.tag == f"{{{W}}}p" and pstyle(e) == "Heading1" and ptext(e).strip() == "PENUTUP")
iend = next(i for i, e in enumerate(kids) if i > i5 and e.tag == f"{{{W}}}p" and ptext(e).strip().upper().startswith("HALAMAN") and "SENGAJA" in ptext(e).upper())
print(f"Bab IV @{i4}, Bab V @{i5}, penanda akhir @{iend}; elemen lama dibuang: {iend - i4 - 2}")

# jangan sampai membuang pemisah seksi (sectPr) di dalam rentang yang akan diganti
sect_in_range = [i for i in range(i4 + 1, iend) if i != i5 and kids[i].find(".//w:sectPr", NS) is not None]
print("sectPr dalam rentang:", sect_in_range)

# ------------------------------------------------------------------------------------------------ penomoran
tnum, gnum = {}, {}
tc = gc = 0
for blk in C.B:
    if blk[0] == "table":
        tc += 1
        tnum[blk[1]] = tc
    elif blk[0] in ("code", "img", "ph"):
        gc += 1
        gnum[blk[1]] = gc


def resolve(t):
    t = re.sub(r"\{T:(\w+)\}", lambda m: f"Tabel 4.{tnum[m.group(1)]}", t)
    t = re.sub(r"\{G:(\w+)\}", lambda m: f"Gambar 4.{gnum[m.group(1)]}", t)
    return t.replace("`", "")


# ------------------------------------------------------------------------------------------------ runs
ITAL = ["browser extension", "content script", "service worker", "extension", "popup", "feature fusion", "feature importance",
        "confusion matrix", "false positive rate", "false positive", "false negative", "hard negative", "domain-first",
        "soft 404", "wildcard", "headless", "User-Agent", "stemming", "stopword", "lowercasing", "holdout", "recall", "precision",
        "accuracy", "F1-score", "random seed", "pickle", "real-time", "embedding", "group k-fold", "feature", "spam", "crash",
        "scaler", "vectorizer", "pipeline", "independent validation set", "sitemap", "class_weight", "script", "style"]
ITAL_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(x) for x in sorted(ITAL, key=len, reverse=True)) + r")(?![\w-])", re.I)
TOK = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def run(text, italic=False, bold=False):
    if not text:
        return ""
    rpr = ("<w:i/>" if italic else "") + ("<w:b/>" if bold else "")
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def runs(text, auto=True):
    out = []
    for part in TOK.split(text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(run(part[2:-2], bold=True))
        elif part.startswith("*"):
            out.append(run(part[1:-1], italic=True))
        elif auto:
            pos = 0
            for m in ITAL_RE.finditer(part):
                out.append(run(part[pos:m.start()]))
                out.append(run(m.group(0), italic=True))
                pos = m.end()
            out.append(run(part[pos:]))
        else:
            out.append(run(part))
    return "".join(out)


def X(xml):
    return etree.fromstring(f"<root {NSDECL}>{xml}</root>")[0]


# ------------------------------------------------------------------------------------------------ pembangun elemen
def P(text, style="Paragraf", extra=""):
    return X(f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra}</w:pPr>{runs(resolve(text))}</w:p>')


def HEAD(level, text):
    return X(f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/><w:spacing w:before="240"/></w:pPr>{run(text)}</w:p>')


def NP(num, text):
    return X(f'<w:p><w:pPr><w:pStyle w:val="Paragraf"/><w:ind w:left="397" w:hanging="397"/></w:pPr>{run(num)}'
             f'<w:r><w:tab/></w:r>{runs(resolve(text))}</w:p>')


def CAP_T(text):
    return X(f'<w:p><w:pPr><w:pStyle w:val="CaptionTabel"/><w:keepNext/><w:spacing w:before="120"/></w:pPr>{run(text)}</w:p>')


def CAP_G(text):
    return X(f'<w:p><w:pPr><w:pStyle w:val="CaptionGambar"/><w:spacing w:after="120"/></w:pPr>{run(text)}</w:p>')


def TABLE(num, caption, header, rows, widths, aligns):
    assert sum(widths) == 5836, (caption, sum(widths))
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    keep_all = len(rows) <= 12   # tabel kecil: jaga tetap satu halaman

    def cell(w, txt, head=False, jc="l", bold=False, keep=False):
        jcx = '<w:jc w:val="center"/>' if (head or jc == "c") else ""
        shd = '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>' if head else ""
        style = "TabelHead" if head else "TabelIsi"
        kn = "<w:keepNext/>" if keep else ""
        r = runs(resolve(txt), auto=False) if not bold else run(resolve(txt), bold=True)
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{kn}{jcx}</w:pPr>{r}</w:p></w:tc>')

    hdr = "".join(cell(w, t, head=True, keep=True) for w, t in zip(widths, header))
    body_rows = ""
    for ri, row in enumerate(rows):
        bold = row[0] == "Total"
        keep = keep_all and ri < len(rows) - 1
        body_rows += '<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(
            cell(w, t, jc=a, bold=bold, keep=keep) for w, t, a in zip(widths, row, aligns)) + "</w:tr>"
    tbl = X('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="5836" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
            '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid><w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>{hdr}</w:tr>{body_rows}</w:tbl>')
    return [CAP_T(f"Tabel 4.{num} {caption}"), tbl, X('<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>')]


_docpr = [9100000]


def CODE(num, caption, lines):
    _docpr[0] += 1
    did = _docpr[0]
    LINE = 107950           # 8,5 pt dalam EMU
    cx = 3700000
    cy = len(lines) * LINE + 2 * 36000 + 25000
    paras = ""
    for ln in lines:
        paras += ('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="170" w:lineRule="exact"/><w:ind w:left="0" w:firstLine="0"/>'
                  '<w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas" w:eastAsia="Consolas"/>'
                  '<w:sz w:val="14"/><w:szCs w:val="14"/><w:lang w:val="en-US"/></w:rPr>'
                  f'<w:t xml:space="preserve">{escape(ln)}</w:t></w:r></w:p>')
    p = X('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
          f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
          f'<wp:docPr id="{did}" name="Kode {did}" descr="Cuplikan kode: {escape(caption)}"/><wp:cNvGraphicFramePr/>'
          '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"><wps:wsp>'
          '<wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" y="0"/>'
          f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
          '<a:solidFill><a:srgbClr val="F2F2F2"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="7F7F7F"/></a:solidFill></a:ln></wps:spPr>'
          f'<wps:txbx><w:txbxContent>{paras}</w:txbxContent></wps:txbx>'
          '<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="72000" tIns="36000" rIns="72000" bIns="36000" anchor="t" anchorCtr="0"><a:noAutofit/></wps:bodyPr>'
          '</wps:wsp></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
    return [p, CAP_G(f"Gambar 4.{num} {caption}")]


def IMG(num, caption, fname, width_cm):
    path = C.IMGD / fname
    tmp = doc.add_paragraph()
    tmp.add_run().add_picture(str(path), width=Cm(width_cm))
    pel = tmp._p
    body.remove(pel)
    ppr = pel.find("w:pPr", NS)
    if ppr is not None:
        pel.remove(ppr)
    pel.insert(0, X('<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'))
    # beri id unik & deskripsi
    for dp in pel.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"):
        _docpr[0] += 1
        dp.set("id", str(_docpr[0]))
        dp.set("name", f"Gambar {_docpr[0]}")
        dp.set("descr", caption)
    return [pel, CAP_G(f"Gambar 4.{num} {caption}")]


def PH(num, caption, instruksi):
    t = X('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="5836" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr>'
          '<w:tblGrid><w:gridCol w:w="5836"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="2200" w:hRule="atLeast"/></w:trPr><w:tc>'
          '<w:tcPr><w:tcW w:w="5836" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/><w:vAlign w:val="center"/></w:tcPr>'
          '<w:p><w:pPr><w:pStyle w:val="TabelIsi"/><w:keepNext/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>[SISIPKAN GAMBAR DI SINI]</w:t></w:r></w:p>'
          f'<w:p><w:pPr><w:pStyle w:val="TabelIsi"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">{escape(instruksi)}</w:t></w:r></w:p>'
          '</w:tc></w:tr></w:tbl>')
    return [t, CAP_G(f"Gambar 4.{num} {caption}")]


def build(blocks, number=True):
    out = []
    for blk in blocks:
        k = blk[0]
        if k == "h2":
            out.append(HEAD(2, blk[1]))
        elif k == "h3":
            out.append(HEAD(3, blk[1]))
        elif k == "p":
            out.append(P(blk[1]))
        elif k == "np":
            out.append(NP(blk[1], blk[2]))
        elif k == "table":
            out += TABLE(tnum[blk[1]], blk[2], blk[3], blk[4], blk[5], blk[6])
        elif k == "code":
            out += CODE(gnum[blk[1]], blk[2], blk[3])
        elif k == "img":
            out += IMG(gnum[blk[1]], blk[2], blk[3], blk[4])
        elif k == "ph":
            out += PH(gnum[blk[1]], blk[2], blk[3])
        else:
            raise ValueError(k)
    return out


new4 = build(C.B)
new5 = build(C.B5)

# ------------------------------------------------------------------------------------------------ ganti isi
h4, h5, endp = kids[i4], kids[i5], kids[iend]
for idx in range(i4 + 1, iend):
    if idx in (i5,):
        continue
    if idx in sect_in_range:
        continue
    body.remove(kids[idx])
anchor = h4
for el in new4:
    anchor.addnext(el)
    anchor = el
anchor = h5
for el in new5:
    anchor.addnext(el)
    anchor = el

doc.save(str(OUT))
print(f"tersimpan: {OUT}  | tabel Bab 4: {tc}, gambar Bab 4: {gc}")
