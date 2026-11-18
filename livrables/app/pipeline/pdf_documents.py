"""Rendu PDF des rapports du projet, avec ReportLab et les polices de matplotlib.

Le contenu Word est parcouru dans son ordre réel (paragraphes, images, tableaux).
Ce moteur couvre les rapports produits ici ; ce n'est pas un convertisseur Word généraliste.
"""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table as WordTable
from docx.text.paragraph import Paragraph as WordParagraph
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, LongTable, TableStyle, PageBreak


def _polices():
    folder = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, filename in [("Vigie", "DejaVuSans.ttf"), ("Vigie-Bold", "DejaVuSans-Bold.ttf"),
                           ("Vigie-Italic", "DejaVuSans-Oblique.ttf"),
                           ("Vigie-BoldItalic", "DejaVuSans-BoldOblique.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
    pdfmetrics.registerFontFamily("Vigie", normal="Vigie", bold="Vigie-Bold",
                                  italic="Vigie-Italic", boldItalic="Vigie-BoldItalic")


def _texte(value):
    # Certains anciens scripts utilisent SUB comme séparateur de parcours.
    return escape(value.replace("\x1a", " → ")).replace("\n", "<br/>").replace("\t", "    ")


def _paragraphe(p, cellule=False):
    name = p.style.name if p.style else "Normal"
    heading = name.startswith("Heading")
    size = 8 if cellule else 9.5
    if heading:
        size = {"Heading 1": 14, "Heading 2": 11.5, "Heading 3": 10}.get(name, 10)
    explicit = [r.font.size.pt for r in p.runs if r.font.size]
    if explicit:
        size = max(explicit)
    fragments = []
    for r in p.runs:
        text = _texte(r.text)
        if r.bold or heading:
            text = "<b>" + text + "</b>"
        if r.italic:
            text = "<i>" + text + "</i>"
        if r.font.color.rgb:
            text = '<font color="#' + str(r.font.color.rgb) + '">' + text + '</font>'
        fragments.append(text)
    text = "".join(fragments) or _texte(p.text)
    bullet = name == "List Bullet"
    alignment = p.alignment
    paragraph_style = p.style
    while alignment is None and paragraph_style is not None:
        alignment = paragraph_style.paragraph_format.alignment
        paragraph_style = paragraph_style.base_style
    pdf_alignment = {
        WD_ALIGN_PARAGRAPH.CENTER: TA_CENTER,
        WD_ALIGN_PARAGRAPH.RIGHT: TA_RIGHT,
        WD_ALIGN_PARAGRAPH.JUSTIFY: TA_JUSTIFY,
    }.get(alignment, TA_LEFT)
    style = ParagraphStyle("contenu", fontName="Vigie", fontSize=size, leading=size * 1.12,
                           spaceBefore=7 if heading else 0, spaceAfter=3 if cellule else 4,
                           keepWithNext=heading, textColor=colors.HexColor("#1F2D3D") if heading else colors.black,
                           alignment=pdf_alignment,
                           leftIndent=10 if bullet else 0, bulletIndent=0)
    return Paragraph(text or "&#160;", style, bulletText="•" if bullet else None)


def exporter_pdf(document, destination):
    """Produit un PDF autonome ; une erreur de rendu interrompt la génération."""
    _polices()
    section = document.sections[0]
    width, height = section.page_width.pt, section.page_height.pt
    left, right = section.left_margin.pt, section.right_margin.pt
    top, bottom = section.top_margin.pt, section.bottom_margin.pt
    available = width - left - right - 12  # marges internes du cadre ReportLab
    story = []
    for element in document.element.body.iterchildren():
        if element.tag == qn("w:p"):
            p = WordParagraph(element, document)
            if p.paragraph_format.page_break_before:
                story.append(PageBreak())
            if p.text:
                story.append(_paragraphe(p))
            for drawing in element.iter(qn("wp:inline")):
                extent = drawing.find(qn("wp:extent"))
                blip = next(drawing.iter(qn("a:blip")), None)
                if extent is None or blip is None:
                    continue
                relation = blip.get(qn("r:embed"))
                blob = document.part.related_parts[relation].blob
                iw, ih = int(extent.get("cx")) / 12700, int(extent.get("cy")) / 12700
                scale = min(1, available / iw, (height - top - bottom - 24) / ih)
                story.append(Image(BytesIO(blob), width=iw * scale, height=ih * scale))
            if not p.text and not list(element.iter(qn("wp:inline"))):
                story.append(Spacer(1, 3))
            if any(b.get(qn("w:type")) == "page" for b in element.iter(qn("w:br"))):
                story.append(PageBreak())
        elif element.tag == qn("w:tbl"):
            table = WordTable(element, document)
            rows = [[[_paragraphe(p, cellule=True) for p in cell.paragraphs] for cell in row.cells]
                    for row in table.rows]
            widths = [col.width.pt if col.width else 1 for col in table.columns]
            widths = [available * w / sum(widths) for w in widths]
            rendered = LongTable(rows, colWidths=widths, repeatRows=1, hAlign="CENTER", splitByRow=1,
                                 splitInRow=1)
            rendered.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EEF6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FB")]),
                ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CCD5DF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.extend([rendered, Spacer(1, 5)])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Vigie", 7.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(width / 2, bottom / 2,
                                 f"VIGIE-Ecole-Team · Data Challenge Burkina 2026 · page {doc.page}")
        canvas.restoreState()

    destination = Path(destination)
    title = next((p.text for p in document.paragraphs if p.text), destination.stem)
    pdf = SimpleDocTemplate(str(destination), pagesize=(width, height), leftMargin=left, rightMargin=right,
                            topMargin=top, bottomMargin=bottom, title=title)
    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return destination
