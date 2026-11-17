"""T04b - Série consolidée du primaire par ancienne province, niveau, sexe (2008-09 à 2024-25).

Choix (vérifiés contre la base principale du challenge, effectifs par ancienne région et par sexe) :
  - 2017-18 à 2024-25 : tableaux détaillés de l'édition de l'année (III.3.3 public + privé),
    extraits le 16/11/2026 (travaux ChatGPT, script conservé dans DATAS/Travaux_ChatGPT_20261116).
    309 cases région-année-sexe sur 312 identiques à la base principale ; 3 écarts de 20 élèves.
  - 2008-09 à 2016-17 : tableau historique VIII.3 (t04_primaire.py, édition la plus récente).
    Le tableau historique est écarté après 2016-17 : répartitions par sexe fausses dans l'édition
    2024-25 (ex. Kadiogo : 182 749 garçons / 424 806 filles pour 299 604 / 307 951 publiés ailleurs)
    et chiffres de 2018-19 révisés après coup.
Sorties : 02_nettoyage effectifs-primaire-provinces-consolide (v2) ; ressources-primaire-provinces ;
          02_nettoyage controle-T04b (contrôle par sexe contre la base principale).
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import ROOT, DATAS, norm, out_path

CG = DATAS / "Travaux_ChatGPT_20261116"
k = ["old_adm2_pcode", "annee_scolaire", "niveau", "sexe"]
hist = pd.read_csv(next((ROOT / "02_nettoyage").glob("*effectifs-primaire-provinces_v1.csv")), sep=";")
hist = hist[hist.annee_scolaire <= "2016/2017"][k + ["effectif", "redoublants", "edition_source", "page_pdf"]]
hist["source"] = "historique VIII.3 (édition " + hist.edition_source + ", p. " + hist.page_pdf.astype(str) + ")"
cont = pd.read_csv(CG / "primaire_contemporain_45_provinces_controle.csv", sep=";")
cont = cont[k + ["effectif", "redoublants", "page_pdf"]].copy()
cont["source"] = "détail III.3.3 de l'édition " + cont.annee_scolaire + " (p. " + cont.page_pdf.astype(str) + ")"
cons = pd.concat([hist[k + ["effectif", "redoublants", "source"]], cont[k + ["effectif", "redoublants", "source"]]])
assert not cons.duplicated(k).any()

# contrôles arithmétiques
w = cons.pivot_table(index=["old_adm2_pcode", "annee_scolaire", "niveau"], columns="sexe", values="effectif")
bad_sexe = int(((w.G + w.F - w["T"]).abs() > 0).sum())
s = cons[cons.niveau != "TOTAL"].groupby(["old_adm2_pcode", "annee_scolaire", "sexe"]).effectif.sum()
t = cons[cons.niveau == "TOTAL"].set_index(["old_adm2_pcode", "annee_scolaire", "sexe"]).effectif
bad_niv = int(((s - t).abs() > 0).sum())
bad_r = int((cons.redoublants > cons.effectif).sum())

# contrôle contre la base principale (ancienne région x année x sexe, 2015-16 à 2024-25)
al = pd.read_csv(next((ROOT / "01_collecte").glob("*alias-noms*")), sep=";")
o = al[(al.niveau == "region") & (al.decoupage == "ancien")]
reg = dict(zip(o.code, o.alias))
f1 = pd.read_excel(next(DATAS.glob("DONNEES_STATISTQUES*.xlsx")), sheet_name="Feuil1", header=None)
rows, cur = [], None
for _, r in f1.iloc[2:].iterrows():
    if isinstance(r[0], str) and r[0].strip():
        cur = r[0].strip()
    sx = {"GARCONS": "G", "FILLES": "F", "TOTAL": "T"}.get(str(r[1]).strip().upper())
    if cur and sx and norm(cur) != "NATIONAL":
        for j, an in enumerate(range(2015, 2025)):
            rows.append({"region": norm(cur), "annee_scolaire": f"{an}/{an + 1}", "sexe": sx, "effectif_base_principale": r[2 + j]})
base = pd.DataFrame(rows)
tt = cons[cons.niveau == "TOTAL"].copy()
tt["region"] = tt.old_adm2_pcode.str[:4].map(reg)
g = tt.groupby(["region", "annee_scolaire", "sexe"], as_index=False).effectif.sum()
ctl = base.merge(g, on=["region", "annee_scolaire", "sexe"], how="left")
ctl["ecart"] = ctl.effectif - ctl.effectif_base_principale
ctl.to_csv(out_path("02-nettoyage", "engineer", "controle-T04b-primaire-vs-base-principale", 2), sep=";", index=False, encoding="utf-8")

cons.sort_values(k).to_csv(out_path("02-nettoyage", "engineer", "effectifs-primaire-provinces-consolide", 2), sep=";", index=False, encoding="utf-8")

# ressources (I.1, public + privé) par ancienne province et année
lg = pd.read_csv(CG / "primaire_tables_contemporaines_long.csv", sep=";")
res = lg[(lg.table_source == "I.1") & (lg.statut_etablissement == "total") & lg.eligible_structure]
res = res.pivot_table(index=["old_adm2_pcode", "annee_scolaire"], columns="variable", values="valeur", aggfunc="first").reset_index()
res.to_csv(out_path("02-nettoyage", "engineer", "ressources-primaire-provinces"), sep=";", index=False, encoding="utf-8")

print("consolidé :", len(cons), "lignes,", cons.annee_scolaire.nunique(), "années,", cons.old_adm2_pcode.nunique(), "provinces")
print("contrôles : G+F≠T", bad_sexe, "| somme niveaux≠total", bad_niv, "| redoublants>effectif", bad_r)
print("base principale :", int((ctl.ecart == 0).sum()), "/", len(ctl), "identiques ; écart max", ctl.ecart.abs().max())
print("ressources :", res.shape, res.columns.tolist())
