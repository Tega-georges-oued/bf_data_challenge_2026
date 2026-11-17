"""Lecture du texte des PDF (avec mise en page), robuste sous Windows, macOS et Linux.

Ordre de recherche :
  1. texte déjà extrait, conservé dans DATAS/Textes_extraits_pdf (aucun outil externe nécessaire) ;
     il n'est utilisé que si l'empreinte MD5 du PDF n'a pas changé ;
  2. pdftotext (poppler), cherché dans le PATH et aux emplacements Windows habituels ; le texte obtenu
     est alors conservé pour les exécutions suivantes ;
  3. sinon : arrêt avec un message qui explique quoi installer.
"""
import hashlib, os, shutil, subprocess, sys
from pathlib import Path
from utils import DATAS

CACHE = DATAS / "Textes_extraits_pdf"


class OutilManquant(RuntimeError):
    pass


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _pdftotext():
    trouve = shutil.which("pdftotext")
    if trouve:
        return trouve
    candidats = []
    for base in [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", ""), str(Path.home())]:
        if base:
            candidats += list(Path(base).glob("poppler*/**/bin/pdftotext.exe")) + list(Path(base).glob("poppler*/bin/pdftotext.exe"))
    conda = Path(sys.prefix) / "Library" / "bin" / "pdftotext.exe"
    candidats.append(conda)
    for c in candidats:
        if c.exists():
            return str(c)
    return None


def texte_pdf(pdf):
    """Renvoie le texte du PDF, pages séparées par le caractère \\f, comme pdftotext -layout."""
    pdf = Path(pdf)
    empreinte = md5(pdf)
    cache = CACHE / f"{pdf.stem}.txt"
    cache_md5 = CACHE / f"{pdf.stem}.md5"
    if cache.exists() and cache_md5.exists() and cache_md5.read_text(encoding="utf-8").strip() == empreinte:
        return cache.read_text(encoding="utf-8")
    outil = _pdftotext()
    if not outil:
        raise OutilManquant(
            f"\nImpossible de lire {pdf.name} :\n"
            f"  - pas de texte déjà extrait et à jour dans {CACHE}\n"
            "  - l'outil pdftotext (poppler) est introuvable.\n"
            "Solutions : 1) récupérer le dossier DATAS/Textes_extraits_pdf livré avec le projet ;\n"
            "            2) ou installer poppler : sous Windows, « conda install -c conda-forge poppler »,\n"
            "               ou télécharger poppler pour Windows et ajouter son dossier bin au PATH.\n")
    r = subprocess.run([outil, "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"pdftotext a échoué sur {pdf.name} : {r.stderr.decode('utf-8', 'replace')[:300]}")
    txt = r.stdout.decode("utf-8", "replace")
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(txt, encoding="utf-8", newline="\n")
        cache_md5.write_text(empreinte, encoding="utf-8")
    except OSError:
        pass
    return txt
