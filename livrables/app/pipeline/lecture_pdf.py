"""Lecture PDF : cache vérifié par MD5, puis extraction avec PyMuPDF installé par pip.

Les extractions historiques sont conservées pour ne pas changer le résultat du parseur.
Pour un nouveau PDF, le mode layout de PyMuPDF conserve l'espacement des colonnes.
"""
import hashlib
import subprocess
import sys
import tempfile
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


def texte_pdf(pdf):
    """Renvoie le texte avec des séparateurs de pages ; aucun outil système requis."""
    pdf = Path(pdf)
    empreinte = md5(pdf)
    cache = CACHE / f"{pdf.stem}.txt"
    cache_md5 = CACHE / f"{pdf.stem}.md5"
    if cache.exists() and cache_md5.exists() and cache_md5.read_text(encoding="utf-8").strip() == empreinte:
        return cache.read_text(encoding="utf-8")
    try:
        import pymupdf  # Vérification de la dépendance avant le sous-processus Python.
    except ImportError as exc:
        raise OutilManquant("PyMuPDF absent : pip install -r livrables/app/requirements.txt") from exc
    with tempfile.TemporaryDirectory(prefix="vigie_pdf_") as temp:
        output = Path(temp) / "texte.txt"
        result = subprocess.run([sys.executable, "-m", "pymupdf", "gettext", "-mode", "layout",
                                 "-output", str(output), str(pdf.resolve())],
                                capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        if result.returncode:
            raise RuntimeError(f"Extraction PyMuPDF impossible pour {pdf.name} : {result.stderr[:300]}")
        txt = output.read_text(encoding="utf-8")
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(txt, encoding="utf-8", newline="\n")
        cache_md5.write_text(empreinte, encoding="utf-8")
    except OSError:
        pass
    return txt
