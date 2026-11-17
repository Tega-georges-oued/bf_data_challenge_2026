"""L01 - Registre des sources : chaque fichier de DATAS, son producteur, sa publication, son lien,
sa date d'extraction, son empreinte MD5 et son statut (doublon, source principale...)."""
import sys, hashlib
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import DATAS, PACK, EXT, out_path

def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

rows = []
def add(path: Path, **kw):
    rows.append({"fichier": str(path.relative_to(DATAS)).replace("\\", "/"), "taille_ko": round(path.stat().st_size / 1024),
                 "md5": md5(path), **kw})

# 1. Base principale remise par les organisateurs
for p in DATAS.glob("DONNEES_STATISTQUES*.xlsx"):
    add(p, groupe="Base principale du challenge", producteur="DGESS / MEBAPLN (remise par les organisateurs)",
        publication="Données statistiques préscolaire et primaire 2016-2025", periode="2015-16 à 2024-25",
        url="Espace challenge equation.africadataentry.com", date_extraction="2026-11-13")

# 2. Data Pack officiel (manifeste des organisateurs)
man = pd.read_csv(PACK / "00_Documentation_et_Referentiels/manifeste_telechargements.csv", sep=";", dtype=str)
for _, m in man.iterrows():
    p = PACK / m.dossier / m.fichier
    if p.exists():
        add(p, groupe="Data Pack DCB 2026", producteur=m.source, publication=m.description, periode="",
            url=m.url, date_extraction="2026-11-11 (Data Pack)")

# 3. Publications DGESS ajoutées par l'équipe (catalogues CNS)
known = {r["md5"]: r["fichier"] for r in rows}
for p in sorted((DATAS / "Annuaires_et_tableaux_de_bord_DGESS_Education_Burkina_hors_superieur").rglob("*.pdf")):
    h = md5(p); mini = "MESFPT" if "MESFPT" in p.parts else "MEBAPLN"
    rows.append({"fichier": str(p.relative_to(DATAS)).replace("\\", "/"), "taille_ko": round(p.stat().st_size / 1024), "md5": h,
                 "groupe": "Publications DGESS ajoutées par l'équipe", "producteur": f"DGESS / {mini} (via CNS)",
                 "publication": p.stem.replace("_", " "), "periode": p.stem.split("_")[-1],
                 "url": "https://www.cns.bf/publications/" + mini.lower().replace("mebapln", "mebapln") + "/",
                 "date_extraction": "2026-11-13",
                 "statut": ("doublon identique de " + known[h]) if h in known else "nouveau (absent du Data Pack)"})

# 4. Sources externes (Open Data for Africa, HDX)
cat = EXT / "OpenDataForAfrica_INSD/DCB_ext_ODA_catalogue-jeux-extraits.csv"
if cat.exists():
    c = pd.read_csv(cat, sep=";", dtype=str)
    for p in sorted((EXT / "OpenDataForAfrica_INSD").glob("DCB_ext_ODA_*.csv")):
        theme = p.stem.replace("DCB_ext_ODA_", "")
        sub = c[c.theme == theme]
        add(p, groupe="Open Data for Africa (portail INSD)",
            producteur="; ".join(sorted(set(sub.source.dropna()))) or "INSD", 
            publication=f"{len(sub)} jeux extraits par l'interface de données du portail (liste : catalogue-jeux-extraits)" if len(sub) else "Catalogue des jeux extraits",
            periode="", url="https://burkinafaso.opendataforafrica.org", date_extraction="2026-11-16")
reg = EXT / "HDX/DCB_ext_HDX_registre-sources.csv"
hdx = pd.read_csv(reg, sep=";", dtype=str) if reg.exists() else pd.DataFrame(columns=["fichier"])
for p in sorted((EXT / "HDX").glob("DCB_ext_HDX_*")):
    if p.name.endswith("registre-sources.csv") or p.suffix == ".zip":
        continue
    m = hdx[hdx.fichier == p.name]
    m = m.iloc[0] if len(m) else {}
    add(p, groupe="HDX (OCHA)", producteur=(m.get("producteur") or m.get("organisation") or ""),
        publication=m.get("jeu", p.stem), periode="", url=m.get("url", "https://data.humdata.org"),
        date_extraction="2026-11-16")

df = pd.DataFrame(rows)
df["statut"] = df.get("statut").fillna("") if "statut" in df else ""
df.insert(0, "id_source", [f"S{i:03d}" for i in range(1, len(df) + 1)])
f = out_path("01-collecte", "engineer", "registre-sources")
df.to_csv(f, sep=";", index=False, encoding="utf-8")
print(f.name, len(df), "fichiers ;", df.groupby("groupe").size().to_dict())
print(df[df.groupe.str.startswith("Publications")].statut.str.split(" de ").str[0].value_counts().to_dict())
