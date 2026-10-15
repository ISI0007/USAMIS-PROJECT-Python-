"""Report document generation.

Produces an *official letterhead* document for each management report:
the JIT crest, the report title, the institution line, a generated-on date,
a reference number, the full report content (totals + tables) and a footer.

Two exporters share one content model:

* :func:`build_pdf`  -> an A4 PDF (selectable text, not an image)
* :func:`build_docx` -> an editable Word document

The content model is built from live database rows, always the *full* report
(independent of any on-screen filters), so the downloaded artefact is complete.
"""
from __future__ import annotations

import datetime as dt
import io
import os


def _ref(prefix: str) -> str:
    """A short, human-readable reference number, e.g. USAMIS-MR-20261015-1538."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    return f"USAMIS-{prefix}-{stamp}"


def _logo_path() -> str | None:
    # app/services/report_documents.py -> app/static/img/jit-logo.png
    here = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(here)
    path = os.path.join(app_dir, "static", "img", "jit-logo.png")
    return path if os.path.exists(path) else None


# --------------------------------------------------------------------------- #
# Content model
# --------------------------------------------------------------------------- #
class ReportDoc:
    def __init__(self, title: str, subtitle: str, reference: str,
                 generated_on: str, tables: list, totals: list | None = None):
        self.title = title
        self.subtitle = subtitle
        self.reference = reference
        self.generated_on = generated_on
        self.tables = tables          # list of {"heading": str, "columns": [...], "rows": [[...]]}
        self.totals = totals or []    # list of (label, value) summary pairs


# --------------------------------------------------------------------------- #
# PDF (letterhead)
# --------------------------------------------------------------------------- #
def build_pdf(doc: ReportDoc) -> bytes:
    import pymupdf

    A4 = pymupdf.paper_rect("a4")
    margin = 48
    maroon = (0.70, 0.01, 0.09)
    navy = (0.10, 0.15, 0.25)
    grey = (0.42, 0.45, 0.47)

    out = pymupdf.open()
    page = out.new_page(width=A4.width, height=A4.height)
    y = margin

    def new_page():
        nonlocal page, y
        page = out.new_page(width=A4.width, height=A4.height)
        y = margin

    def ensure(space):
        nonlocal y
        if y + space > A4.height - margin - 20:
            new_page()

    # ---- letterhead ----
    logo = _logo_path()
    if logo:
        try:
            page.insert_image(pymupdf.Rect(margin, y, margin + 62, y + 62), filename=logo)
        except Exception:
            pass
    tx = margin + 76
    page.insert_text((tx, y + 20), "Jinling Institute of Technology",
                     fontname="hebo", fontsize=15, color=navy)
    page.insert_text((tx, y + 38), "USAMIS · Student Academic Management Information System",
                     fontname="helv", fontsize=9.5, color=grey)
    page.insert_text((tx, y + 53), "Department of Software Engineering",
                     fontname="helv", fontsize=9.5, color=grey)
    y += 70
    page.draw_line(pymupdf.Point(margin, y), pymupdf.Point(A4.width - margin, y),
                   color=maroon, width=2)
    y += 22

    # ---- title block ----
    page.insert_text((margin, y), doc.title, fontname="hebo", fontsize=18, color=maroon)
    y += 20
    page.insert_text((margin, y), doc.subtitle, fontname="helv", fontsize=10.5, color=grey)
    y += 16
    page.insert_text((margin, y), f"Reference: {doc.reference}", fontname="helv", fontsize=9.5, color=navy)
    page.insert_text((A4.width - margin - 150, y), f"Generated: {doc.generated_on}",
                     fontname="helv", fontsize=9.5, color=navy)
    y += 22

    def wrap(text, font, size, width):
        words, lines, cur = str(text).split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if pymupdf.get_text_length(trial, fontname=font, fontsize=size) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines or [""]

    # ---- totals summary ----
    if doc.totals:
        ensure(30 + len(doc.totals) * 15)
        page.insert_text((margin, y), "Summary", fontname="hebo", fontsize=12, color=navy)
        y += 18
        for label, value in doc.totals:
            page.insert_text((margin, y), str(label), fontname="helv", fontsize=10, color=(0.15, 0.15, 0.15))
            vw = pymupdf.get_text_length(str(value), fontname="hebo", fontsize=10)
            page.insert_text((A4.width - margin - vw, y), str(value), fontname="hebo", fontsize=10, color=navy)
            y += 15
        y += 8

    # ---- tables ----
    for tbl in doc.tables:
        ensure(40)
        page.insert_text((margin, y), tbl["heading"], fontname="hebo", fontsize=12, color=navy)
        y += 16
        cols = tbl["columns"]
        rows = tbl["rows"]
        usable = A4.width - 2 * margin
        col_w = usable / max(len(cols), 1)

        # header row
        page.draw_rect(pymupdf.Rect(margin, y - 10, A4.width - margin, y + 6),
                       color=None, fill=(0.96, 0.93, 0.93))
        for i, c in enumerate(cols):
            page.insert_text((margin + 6 + i * col_w, y), str(c),
                             fontname="hebo", fontsize=9, color=maroon)
        y += 16

        for r in rows:
            ensure(16)
            for i, cell in enumerate(r):
                txt = str(cell)
                # truncate long cells to the column width
                while pymupdf.get_text_length(txt, fontname="helv", fontsize=9) > col_w - 10 and len(txt) > 4:
                    txt = txt[:-2]
                if txt != str(cell):
                    txt += "…"
                page.insert_text((margin + 6 + i * col_w, y), txt,
                                 fontname="helv", fontsize=9, color=(0.15, 0.15, 0.15))
            y += 14
        if not rows:
            page.insert_text((margin + 6, y), "No data.", fontname="helv", fontsize=9, color=grey)
            y += 14
        y += 10

    # ---- footer on every page ----
    total_pages = out.page_count
    for pno in range(total_pages):
        p = out[pno]
        p.insert_text((margin, A4.height - 30),
                      f"{doc.reference} · USAMIS Management Reports · Page {pno + 1} of {total_pages}",
                      fontname="helv", fontsize=8, color=grey)

    buf = io.BytesIO()
    out.save(buf)
    out.close()
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# DOCX (editable)
# --------------------------------------------------------------------------- #
def build_docx(doc: ReportDoc) -> bytes:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    d = Document()
    sec = d.sections[0]
    sec.top_margin = Inches(0.7)
    sec.bottom_margin = Inches(0.7)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)

    logo = _logo_path()
    if logo:
        p = d.add_paragraph()
        p.add_run().add_picture(logo, width=Inches(0.75))

    h = d.add_paragraph()
    r = h.add_run("Jinling Institute of Technology")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor(0x1A, 0x26, 0x40)
    for line in ("USAMIS · Student Academic Management Information System",
                 "Department of Software Engineering"):
        sp = d.add_paragraph()
        rr = sp.add_run(line)
        rr.font.size = Pt(9)
        rr.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    t = d.add_paragraph()
    tr = t.add_run(doc.title)
    tr.bold = True
    tr.font.size = Pt(18)
    tr.font.color.rgb = RGBColor(0xB3, 0x02, 0x16)

    s = d.add_paragraph()
    sr = s.add_run(doc.subtitle)
    sr.font.size = Pt(10.5)
    sr.italic = True

    m = d.add_paragraph()
    mr = m.add_run(f"Reference: {doc.reference}     Generated: {doc.generated_on}")
    mr.font.size = Pt(9.5)

    if doc.totals:
        d.add_heading("Summary", level=2)
        tt = d.add_table(rows=0, cols=2)
        for label, value in doc.totals:
            row = tt.add_row().cells
            row[0].text = str(label)
            row[1].text = str(value)

    for tbl in doc.tables:
        d.add_heading(tbl["heading"], level=2)
        cols = tbl["columns"]
        rows = tbl["rows"]
        if rows:
            t = d.add_table(rows=1, cols=len(cols))
            t.style = "Light Grid Accent 1"
            for i, c in enumerate(cols):
                t.rows[0].cells[i].text = str(c)
            for r in rows:
                cells = t.add_row().cells
                for i in range(len(cols)):
                    cells[i].text = str(r[i]) if i < len(r) else ""
        else:
            d.add_paragraph("No data.")

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
