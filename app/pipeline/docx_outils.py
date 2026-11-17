"""Outils communs pour produire les documents Word (puis PDF via LibreOffice)."""
import subprocess
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BLEU = RGBColor(0x1F, 0x2D, 0x3D)

def nouveau(titre, sous_titre=None):
    d = Document()
    for s in d.sections:
        s.top_margin = s.bottom_margin = Cm(1.8); s.left_margin = s.right_margin = Cm(2)
    st = d.styles["Normal"]; st.font.name = "DejaVu Sans"; st.font.size = Pt(9.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "DejaVu Sans")
    st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.12
    for lvl, size in [(1, 14), (2, 11.5), (3, 10)]:
        h = d.styles[f"Heading {lvl}"]; h.font.name = "DejaVu Sans"; h.font.size = Pt(size); h.font.color.rgb = BLEU; h.font.bold = True
        h.element.rPr.rFonts.set(qn("w:eastAsia"), "DejaVu Sans")
        h.paragraph_format.space_before = Pt(10 if lvl == 1 else 6); h.paragraph_format.space_after = Pt(3)
    p = d.add_paragraph(); r = p.add_run(titre); r.bold = True; r.font.size = Pt(18); r.font.color.rgb = BLEU
    if sous_titre:
        p = d.add_paragraph(); r = p.add_run(sous_titre); r.font.size = Pt(10); r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    pied(d)
    return d

def pied(d):
    p = d.sections[0].footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("VIGIE-Ecole-Team · Data Challenge Burkina 2026 · page "); r.font.size = Pt(7.5)
    for t, x in [("begin", None), (None, "PAGE"), ("end", None)]:
        run = p.add_run(); run.font.size = Pt(7.5)
        if t:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); run._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = x; run._r.append(e)

def para(d, texte, gras_debut=None, taille=None, italique=False, couleur=None):
    p = d.add_paragraph()
    if gras_debut:
        r = p.add_run(gras_debut); r.bold = True
        if taille: r.font.size = Pt(taille)
    r = p.add_run(texte); r.italic = italique
    if taille: r.font.size = Pt(taille)
    if couleur: r.font.color.rgb = couleur
    return p

def puces(d, items):
    for it in items:
        p = d.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True; p.add_run(it[1])
        else:
            p.add_run(it)

def tableau(d, entetes, lignes, largeurs=None, taille=8):
    t = d.add_table(rows=1, cols=len(entetes)); t.style = "Light Grid Accent 1"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(entetes):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(taille)
    for l in lignes:
        cells = t.add_row().cells
        for i, v in enumerate(l):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(taille)
    if largeurs:
        t.autofit = False
        for i, w in enumerate(largeurs):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(largeurs):
                row.cells[i].width = Cm(w)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def image(d, chemin, largeur_cm=16, legende=None):
    d.add_picture(str(chemin), width=Cm(largeur_cm)); d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if legende:
        p = d.add_paragraph(); r = p.add_run(legende); r.italic = True; r.font.size = Pt(8)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

def _soffice():
    import shutil
    for c in ["soffice", "libreoffice", r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        if shutil.which(c) or Path(c).exists():
            return c
    return None

def enregistrer(d, chemin_docx, pdf=True):
    """Enregistre en Word, puis convertit en PDF avec LibreOffice. Renvoie le PDF, ou None si LibreOffice est absent."""
    chemin_docx = Path(chemin_docx); d.save(chemin_docx)
    if not pdf:
        return None
    so = _soffice()
    if not so:
        print(f"  LibreOffice introuvable : {chemin_docx.name} reste en Word (PDF non produit).")
        return None
    try:
        subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", str(chemin_docx.parent), str(chemin_docx)],
                       check=True, capture_output=True, timeout=180)
    except Exception as e:
        print(f"  Conversion PDF impossible pour {chemin_docx.name} ({type(e).__name__}) : le document reste en Word. "
              "Fermer LibreOffice ou Word s'ils sont ouverts, puis relancer cette étape pour obtenir le PDF.")
        return None
    pdf = chemin_docx.with_suffix(".pdf")
    return pdf if pdf.exists() else None
