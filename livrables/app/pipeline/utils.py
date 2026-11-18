"""Fonctions communes du pipeline VIGIE-École."""
import re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # BF_DATA_CHALLENGE
LIVRABLES = ROOT / "livrables"
DATAS = ROOT / "donnees"
PACK = DATAS / "DataPack_DCB_2026" / "DataPack_DCB_2026"
PACK_CSV = PACK / "data"
EXT = DATAS / "Sources_externes"
TEAM = "VIGIE-Ecole-Team"

def out_path(etape: str, role: str, desc: str, version: int = 1, ext: str = "csv") -> Path:
    """Chemin normalisé : VIGIE-Ecole-Team_ETAPE_D1_ROLE_description_vN.ext dans le dossier de l'étape."""
    folder = LIVRABLES / etape.replace("-", "_", 1)  # '01-collecte' -> dossier 01_collecte
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{TEAM}_{etape}_D1_{role}_{desc}_v{version}.{ext}"

def norm(s) -> str:
    """Nom normalisé pour les jointures : majuscules, sans accents ni ponctuation."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).strip().upper()
    return re.sub(r"\s+", " ", s)

def num(s):
    """'306 926' ou '78,2' -> float ; None si vide."""
    if s is None:
        return None
    s = str(s).replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", ".").strip("*% ")
    try:
        return float(s)
    except ValueError:
        return None
