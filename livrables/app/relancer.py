"""Relance toute la chaîne VIGIE-École, de la collecte aux livrables, puis contrôle les sorties.

Usage (depuis le dossier BF_DATA_CHALLENGE, sous Windows, macOS ou Linux) :
    python livrables/app/relancer.py                 # contrôle de l'environnement, puis toutes les étapes
    python livrables/app/relancer.py --depuis t09    # à partir d'une étape
    python livrables/app/relancer.py --verifier      # contrôle de l'environnement seulement
    python livrables/app/relancer.py --liste         # affiche les étapes
Sous Windows, « py livrables\\app\\relancer.py » fonctionne aussi.
Puis : streamlit run livrables/app/app.py
Chaque exécution est consignée dans livrables/app/relancer_journal.txt.
"""
import argparse, datetime, importlib, importlib.util, os, subprocess, sys, time
from pathlib import Path

APP = Path(__file__).resolve().parent
PIPE = APP / "pipeline"
ROOT = APP.parent.parent
DATAS = ROOT / "donnees"
JOURNAL = APP / "relancer_journal.txt"

# Console Windows : forcer l'UTF-8 pour les accents et les symboles.
for flux in (sys.stdout, sys.stderr):
    try:
        flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ETAPES = [
    ("t02", "t02_referentiel.py", "01 Collecte : référentiel 17 régions, 47 provinces, 351 communes"),
    ("t03", "t03_registre_sources.py", "01 Collecte : registre des sources"),
    ("t04", "t04_primaire.py", "02 Nettoyage : tableaux historiques du primaire"),
    ("t04b", "t04b_consolider_primaire.py", "02 Nettoyage : série du primaire consolidée"),
    ("t07", "t07_indicateurs.py", "03 Transformation : abandon publié et corrigé"),
    ("t08", "t08_facteurs.py", "03 Transformation : table d'analyse et facteurs"),
    ("t09", "t09_modele.py", "04 Analyse : validation, prévision, facteurs, typologie"),
    ("t14", "t14_fiches_atlas.py", "05 Interprétation : fiches des 17 régions et atlas"),
    ("t15a", "t15a_dictionnaire.py", "03 Transformation : dictionnaire des variables"),
    ("t15b", "t15b_schema_parcours_fiabilite.py", "03-04 : schéma, parcours, rapport de fiabilité"),
    ("t15c", "t15c_documentation.py", "05 Interprétation : documentation"),
    ("t16", "t16_lisez_moi.py", "Tous les dépôts : LISEZ-MOI"),
]
ATTENDUS = {
    "01_collecte": ["referentiel-communes-17-regions", "passage-anciennes-provinces-47-provinces", "registre-sources"],
    "02_nettoyage": ["effectifs-primaire-provinces-consolide", "ressources-primaire-provinces"],
    "03_transformation": ["indicateurs-decrochage-47-provinces", "indicateurs-decrochage-17-regions", "table-analyse-47-provinces",
                          "dictionnaire-variables", "schema-donnees", "parcours-donnees"],
    "04_analyse": ["prevision-abandon-primaire-2024-25-47-provinces", "bilan-modele", "rapport-fiabilite", "typologie-17-regions"],
    "05_interpretation": ["fiches-17-regions", "atlas-national", "documentation"],
}
# module importé -> (nom pip, version minimale, étapes qui en ont besoin ; None = application seulement)
PAQUETS = [
    ("pymupdf", "PyMuPDF", "1.24", "lecture PDF"),
    ("pandas", "pandas", "2.2", "toutes"), ("numpy", "numpy", "1.24", "toutes"), ("openpyxl", "openpyxl", "3.1", "t02-t08"),
    ("sklearn", "scikit-learn", "1.3", "t09"), ("shap", "shap", "0.44", "t09"), ("matplotlib", "matplotlib", "3.7", "t14-t15"),
    ("reportlab", "reportlab", "4.0", "t14"), ("docx", "python-docx", "1.1", "t15"),
    ("streamlit", "streamlit", "1.30", None), ("plotly", "plotly", "5.18", None),
]


class Journal:
    def __init__(self):
        self.f = open(JOURNAL, "a", encoding="utf-8")
        self.f.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} · {' '.join(sys.argv[1:]) or 'toutes les étapes'}\n")
    def __call__(self, msg=""):
        print(msg, flush=True); self.f.write(msg + "\n"); self.f.flush()

log = Journal()


def vers_tuple(v):
    out = []
    for p in str(v).split(".")[:3]:
        n = "".join(c for c in p if c.isdigit())
        out.append(int(n) if n else 0)
    return tuple(out + [0] * (3 - len(out)))


def verifier_environnement(sources=True):
    """Renvoie (bloquants, avertissements). sources=False : reprise après t08, les sources brutes ne sont pas relues."""
    bloq, avert = [], []
    if sys.version_info < (3, 10):
        bloq.append(f"Python {sys.version.split()[0]} : il faut Python 3.10 ou plus récent.")
    for mod, pipnom, vmin, usage in PAQUETS:
        try:
            m = importlib.import_module(mod)
            v = getattr(m, "__version__", "0")
            if vers_tuple(v) < vers_tuple(vmin):
                (avert if usage is None else bloq).append(f"{pipnom} {v} trop ancien (minimum {vmin}) : pip install -U \"{pipnom}>={vmin}\"")
        except Exception as e:
            msg = f"{pipnom} absent ({type(e).__name__}) : pip install \"{pipnom}>={vmin}\""
            (avert if usage is None else bloq).append(msg + ("" if usage else " (nécessaire pour l'application)"))
    if not sources:
        pass
    elif not DATAS.exists():
        bloq.append(f"Dossier des sources introuvable : {DATAS}")
    else:
        pack = DATAS / "DataPack_DCB_2026" / "DataPack_DCB_2026"
        if not pack.exists():
            bloq.append(f"Data Pack introuvable : {pack}")
        ann = pack / "01_Education_MENAPLN_DGESS/CNS_DGESS/Annuaires"
        n_pdf = len(list(ann.glob("CNS5*.pdf"))) if ann.exists() else 0
        n_txt = len(list((DATAS / "Textes_extraits_pdf").glob("CNS5*.txt")))
        if n_txt < 8 and importlib.util.find_spec("pymupdf") is None:
            bloq.append(f"Annuaires : {n_txt} textes extraits sur 8 dans donnees/Textes_extraits_pdf et PyMuPDF absent. "
                        "Installer les dépendances : pip install -r livrables/app/requirements.txt.")
        if n_pdf < 8:
            bloq.append(f"Annuaires du primaire : {n_pdf} PDF trouvés sur 8 dans {ann}")
        if not (ROOT / "livrables/02_nettoyage/extractions_sources_20261116").exists():
            bloq.append("Dossier livrables/02_nettoyage/extractions_sources_20261116 introuvable (tableaux extraits et vérifiés utilisés aux étapes t04b et t08).")
    try:
        import matplotlib
        if not (Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf").exists():
            bloq.append("Police DejaVu Sans absente de matplotlib : réinstaller matplotlib.")
    except Exception:
        pass
    sys.path.insert(0, str(PIPE))
    try:
        test = ROOT / "livrables" / "04_analyse" / ".test_ecriture"
        test.write_text("ok", encoding="utf-8"); test.unlink()
    except Exception as e:
        bloq.append(f"Écriture impossible dans les dépôts ({e}). Fermer les fichiers ouverts dans Excel ou un lecteur PDF, puis relancer.")
    return bloq, avert


def lancer(code, fichier, titre, env):
    log(f"\n=== {code} · {titre}")
    t0 = time.time()
    p = subprocess.Popen([sys.executable, str(PIPE / fichier)], cwd=PIPE, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    dernieres = []
    for ligne in p.stdout:
        ligne = ligne.rstrip("\n"); log(ligne)
        dernieres = (dernieres + [ligne])[-15:]
    p.wait()
    if p.returncode:
        texte = "\n".join(dernieres)
        conseil = ""
        if "PermissionError" in texte:
            conseil = "Un fichier de sortie est sans doute ouvert (Excel, lecteur PDF) : le fermer, puis relancer."
        elif "ModuleNotFoundError" in texte or "ImportError" in texte:
            conseil = "Bibliothèque manquante : pip install -r livrables/app/requirements.txt"
        elif "FileNotFoundError" in texte:
            conseil = "Fichier d'entrée introuvable : vérifier le dossier donnees et les dépôts des étapes précédentes."
        elif "MemoryError" in texte:
            conseil = "Mémoire insuffisante : fermer d'autres programmes, puis relancer cette étape."
        log(f"\nÉCHEC à l'étape {code} ({fichier}).")
        if conseil:
            log("Cause probable : " + conseil)
        log(f"Après correction : python livrables/app/relancer.py --depuis {code}   (détail : {JOURNAL.name})")
        return False
    log(f"    terminé en {time.time() - t0:.0f} s")
    return True


def controler_sorties():
    log("\n=== Contrôle des sorties")
    ok = True
    for dossier, motifs in ATTENDUS.items():
        for m in motifs:
            trouve = list((ROOT / "livrables" / dossier).glob(f"*{m}*"))
            log(f"  {'OK    ' if trouve else 'MANQUE'} {dossier}/{m}"); ok &= bool(trouve)
    n = len(list((ROOT / "livrables" / "05_interpretation").glob("*fiche-region-*.pdf")))
    log(f"  {'OK    ' if n == 17 else 'MANQUE'} 05_interpretation : {n} fiches régionales sur 17"); ok &= n == 17
    return ok


def main():
    ap = argparse.ArgumentParser(description="Relance la chaîne VIGIE-École.")
    ap.add_argument("--depuis", default=None, help="code de l'étape de départ (voir --liste)")
    ap.add_argument("--liste", action="store_true"); ap.add_argument("--verifier", action="store_true")
    a = ap.parse_args()
    codes = [c for c, _, _ in ETAPES]
    if a.liste:
        for c, f, t in ETAPES: print(f"{c:5} {f:38} {t}")
        return 0
    if a.depuis and a.depuis not in codes:
        log(f"Étape inconnue : {a.depuis}. Étapes possibles : {', '.join(codes)}"); return 2

    log("=== Contrôle de l'environnement")
    log(f"  Python {sys.version.split()[0]} · {sys.platform} · {ROOT}")
    debut = codes.index(a.depuis) if a.depuis else 0
    bloq, avert = verifier_environnement(sources=debut <= codes.index("t08"))
    for m in avert: log("  ATTENTION : " + m)
    for m in bloq: log("  BLOQUANT  : " + m)
    if bloq:
        log("\nCorriger les points bloquants ci-dessus (souvent : pip install -r livrables/app/requirements.txt), puis relancer.")
        return 1
    log("  Environnement prêt.")
    if a.verifier:
        return 0

    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1")
    for c, f, t in ETAPES[debut:]:
        if not lancer(c, f, t, env):
            return 1
    ok = controler_sorties()
    log("\nTout est en place. Lancer l'application : streamlit run livrables/app/app.py" if ok else "\nDes sorties manquent : voir ci-dessus.")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\nInterrompu. Reprendre avec --depuis <étape>."); sys.exit(130)
