# -*- coding: utf-8 -*-
"""Small Word (python-docx) helpers for build_report.py: headings, paragraphs, bullets, tables, figures and native
Office Math (OMML) equations."""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


# ------------------------------------------------------------------ OMML pieces
def r(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return '<m:r><m:t xml:space="preserve">%s</m:t></m:r>' % t


def fr(a, b):
    return "<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>" % (a, b)


def sb(a, b):
    return "<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>" % (a, b)


def par(a, beg="(", end=")"):
    return '<m:d><m:dPr><m:begChr m:val="%s"/><m:endChr m:val="%s"/></m:dPr><m:e>%s</m:e></m:d>' % (beg, end, a)


def f2(v, n=2):
    return "-" if v is None else ("%.*f" % (n, v))


# ------------------------------------------------------------------ document
class Doc:
    def __init__(self):
        self.d = Document()
        s = self.d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(2.0)
        st = self.d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        for lvl, size in ((1, 15), (2, 12.5), (3, 11)):
            h = self.d.styles["Heading %d" % lvl]
            h.font.name = "Calibri"; h.font.size = Pt(size); h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
            h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        self.fig = 0; self.tab = 0; self.eq = 0

    def H(self, t, lvl=1):
        self.d.add_heading(t, lvl)

    def P(self, t="", bold=False, italic=False, size=None, align=None):
        p = self.d.add_paragraph()
        if t:
            run = p.add_run(t); run.bold = bold; run.italic = italic
            if size:
                run.font.size = Pt(size)
        if align is not None:
            p.alignment = align
        p.paragraph_format.space_after = Pt(4)
        return p

    def B(self, t):
        p = self.d.add_paragraph(style="List Bullet"); p.add_run(t); p.paragraph_format.space_after = Pt(2)
        return p

    def EQ(self, xml, where=None):
        self.eq += 1
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p._p.append(parse_xml('<m:oMathPara %s><m:oMath>%s%s</m:oMath></m:oMathPara>' % (M, xml, r("        (%d)" % self.eq))))
        if where:
            q = self.d.add_paragraph(); rr = q.add_run(where); rr.font.size = Pt(8.5); rr.italic = True
            q.paragraph_format.space_after = Pt(6)
        return self.eq

    def _shade(self, cell, hexcol):
        tcPr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcol)
        tcPr.append(sh)

    def T(self, header, rows, caption, size=8, widths=None):
        self.tab += 1
        cp = self.P("Table %d. %s" % (self.tab, caption), bold=True, size=9); cp.paragraph_format.keep_with_next = True
        t = self.d.add_table(rows=1 + len(rows), cols=len(header)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, h in enumerate(header):
            cell = t.rows[0].cells[j]; cell.text = ""
            run = cell.paragraphs[0].add_run(str(h)); run.bold = True; run.font.size = Pt(size)
            self._shade(cell, "D9E2F3")
        for i, row in enumerate(rows, start=1):
            for j, v in enumerate(row):
                cell = t.rows[i].cells[j]; cell.text = ""
                run = cell.paragraphs[0].add_run("" if v is None else str(v)); run.font.size = Pt(size)
        if widths:
            for row in t.rows:
                for j, w in enumerate(widths):
                    row.cells[j].width = Cm(w)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)
        return self.tab

    def F(self, path, caption, width=15.5):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.fig += 1
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(path, width=Cm(width)); p.paragraph_format.keep_with_next = True
        self.P("Figure %d. %s" % (self.fig, caption), italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
        return self.fig
