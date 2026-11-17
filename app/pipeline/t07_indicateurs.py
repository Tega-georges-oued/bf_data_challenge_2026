"""T07 - Indicateurs de décrochage par province et année, sur le nouveau découpage (47 provinces, 17 régions).

PRIMAIRE (cohorte reconstituée, méthode ISU/DGESS, vérifiée contre le tableau I.8 publié) :
  pour le niveau g (CP1..CM1), de l'année t à t+1 :
    promus  = effectif(g+1, t+1) - redoublants(g+1, t+1)
    redoub  = redoublants(g, t+1)
    sortie  = effectif(g, t) - promus - redoub        (peut être négatif : arrivées nettes)
  - taux_abandon_dgess : sorties par niveau ramenées à 0 si négatives (convention de l'annuaire)
  - taux_sortie_nette  : somme signée des sorties / effectif CP1..CM1
  - taux_abandon_corrige : sortie nette corrigée des fermetures et réouvertures d'écoles
        effet_fermetures = effectif CP1..CM1 x (1 - écoles(t+1)/écoles(t))   (positif : fermetures)
        abandon corrigé = max(0, sortie nette - effet_fermetures) / effectif
    (approximation documentée : une école fermée = perte proportionnelle des élèves ; disponible
     quand le nombre d'écoles est publié, 2017-18 à 2024-25)
  CM2 exclu : la sortie de fin de cycle n'est pas un abandon.
POST-PRIMAIRE ET SECONDAIRE : taux d'abandon publiés par province, classe et sexe (MESFPT, tableau
  II.3.11, extraction contrôlée) ; le taux publié dans l'annuaire t décrit le passage de t-1 à t.
  post-primaire = moyenne 6e, 5e, 4e ; secondaire = moyenne 2nde, 1ère (3e et terminale : classes d'examen).
Report sur 47 provinces : les nombres (effectifs, sorties) sont répartis par les poids de population
2019 (Soum et Tapoa scindés), puis les taux recalculés. Les taux post-primaires sont pondérés par l'effectif.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import ROOT, DATAS, out_path

NIV = ["CP1", "CP2", "CE1", "CE2", "CM1", "CM2"]
c = pd.read_csv(next((ROOT / "02_nettoyage").glob("*effectifs-primaire-provinces-consolide_v2.csv")), sep=";")
E = c.set_index(["old_adm2_pcode", "annee_scolaire", "sexe", "niveau"])[["effectif", "redoublants"]]
years = sorted(c.annee_scolaire.unique())
rows = []
for p in sorted(c.old_adm2_pcode.unique()):
    for t0, t1 in zip(years[:-1], years[1:]):
        for sx in "GFT":
            eff = srt = srt_pos = 0.0
            det = {}
            try:
                for i, g in enumerate(NIV[:-1]):
                    e = E.loc[(p, t0, sx, g), "effectif"]
                    promus = E.loc[(p, t1, sx, NIV[i + 1]), "effectif"] - E.loc[(p, t1, sx, NIV[i + 1]), "redoublants"]
                    red = E.loc[(p, t1, sx, g), "redoublants"]
                    s = e - promus - red
                    eff += e; srt += s; srt_pos += max(0.0, s)
                    det[f"abandon_{g}_pct"] = round(100 * s / e, 2) if e else np.nan
            except KeyError:
                continue
            rows.append({"old_adm2_pcode": p, "annee_depart": t0, "annee_arrivee": t1, "sexe": sx,
                         "effectif_cp1_cm1": eff, "sorties_nettes": srt, "sorties_positives": srt_pos, **det})
pr = pd.DataFrame(rows)

# fermetures / réouvertures : nombre d'écoles (public + privé) publié
res = pd.read_csv(next((ROOT / "02_nettoyage").glob("*ressources-primaire-provinces*")), sep=";")
ec = res.set_index(["old_adm2_pcode", "annee_scolaire"]).ecoles
# écoles non publiées quand la province n'a aucun élève (Komandjari 2022-23 : effectif publié nul) -> 0
tot = c[(c.niveau == "TOTAL") & (c.sexe == "T")].set_index(["old_adm2_pcode", "annee_scolaire"]).effectif
for key, v in tot[tot == 0].items():
    if key[1] >= "2017/2018" and key not in ec.index:
        ec.loc[key] = 0
pr["ecoles_depart"] = [ec.get((p, t), np.nan) for p, t in zip(pr.old_adm2_pcode, pr.annee_depart)]
pr["ecoles_arrivee"] = [ec.get((p, t), np.nan) for p, t in zip(pr.old_adm2_pcode, pr.annee_arrivee)]
pr["choc_ecoles"] = np.where(pr.ecoles_depart > 0, 1 - pr.ecoles_arrivee / pr.ecoles_depart.replace(0, np.nan), 0.0)  # >0 fermetures, <0 réouvertures
pr.loc[pr.ecoles_depart.isna() | pr.ecoles_arrivee.isna(), "choc_ecoles"] = np.nan
pr["effet_fermetures"] = pr.effectif_cp1_cm1 * pr.choc_ecoles

# --- report sur les 47 provinces ---------------------------------------------------
w = pd.read_csv(next((ROOT / "01_collecte").glob("*passage-anciennes-provinces*")), sep=";")
m = pr.merge(w[["old_adm2_pcode", "adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name", "poids_pop_2019"]], on="old_adm2_pcode")
for col in ["effectif_cp1_cm1", "sorties_nettes", "sorties_positives", "effet_fermetures"]:
    m[col] = m[col] * m.poids_pop_2019
def finalize(g, keys):
    a = g.groupby(keys, as_index=False).agg(effectif_cp1_cm1=("effectif_cp1_cm1", "sum"), sorties_nettes=("sorties_nettes", "sum"),
                                            sorties_positives=("sorties_positives", "sum"),
                                            effet_fermetures=("effet_fermetures", lambda s: s.sum(min_count=len(s))))
    a["taux_abandon_dgess"] = 100 * a.sorties_positives / a.effectif_cp1_cm1
    a["taux_sortie_nette"] = 100 * a.sorties_nettes / a.effectif_cp1_cm1
    a["taux_effet_fermetures"] = 100 * a.effet_fermetures / a.effectif_cp1_cm1
    a["taux_abandon_corrige"] = 100 * np.maximum(0, a.sorties_nettes - a.effet_fermetures) / a.effectif_cp1_cm1
    a.loc[a.effet_fermetures.isna(), "taux_abandon_corrige"] = np.nan
    return a
k47 = ["adm1_pcode", "adm1_name", "adm2_pcode", "adm2_name", "annee_depart", "annee_arrivee", "sexe"]
p47 = finalize(m, k47)
r17 = finalize(m, ["adm1_pcode", "adm1_name", "annee_depart", "annee_arrivee", "sexe"])
nat = finalize(m.assign(pays="BF"), ["pays", "annee_depart", "annee_arrivee", "sexe"])

# --- post-primaire et secondaire (taux publiés) -------------------------------------
s = pd.read_csv(DATAS / "Travaux_ChatGPT_20261116/secondaire_provinces_long.csv", sep=";")
f = s[(s.table_source == "II.3.11") & (s.variable == "taux_abandon") & (s.statut_valeur != "manquant_publie") & s.eligible_analyse]
f = f[f.niveau.isin(["6e", "5e", "4e", "2nde", "1ere"])]
f["cycle"] = np.where(f.niveau.isin(["6e", "5e", "4e"]), "post_primaire", "secondaire")
f["an_pub"] = f.annee_scolaire.str[:4].astype(int)
f["annee_depart"] = (f.an_pub - 1).astype(str) + "/" + f.an_pub.astype(str)
f["annee_arrivee"] = f.annee_scolaire
pp = f.groupby(["old_adm2_pcode", "annee_depart", "annee_arrivee", "sexe", "cycle"], as_index=False).valeur.mean()
eff = s[(s.variable == "eleves_scolarises") & (s.table_source == "II.3.3") & (s.sexe == "T")]
eff = eff[eff.niveau == "postprimaire"][["old_adm2_pcode", "annee_scolaire", "valeur"]].rename(columns={"annee_scolaire": "annee_depart", "valeur": "poids_eleves"})
pp = pp.merge(eff, on=["old_adm2_pcode", "annee_depart"], how="left")
pp["poids_eleves"] = pp.poids_eleves.fillna(pp.groupby("old_adm2_pcode").poids_eleves.transform("median")).fillna(1)
pp = pp.merge(w[["old_adm2_pcode", "adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name", "poids_pop_2019"]], on="old_adm2_pcode")
pp["wv"] = pp.poids_eleves * pp.poids_pop_2019
def wavg(g, keys):
    return g.groupby(keys).apply(lambda d: np.average(d.valeur, weights=d.wv), include_groups=False).rename("taux_abandon_publie").reset_index()
pp47 = wavg(pp, k47 + ["cycle"]).pivot_table(index=k47, columns="cycle", values="taux_abandon_publie").reset_index()
pp47.columns = [f"taux_abandon_{c}" if c in ("post_primaire", "secondaire") else c for c in pp47.columns]
p47 = p47.merge(pp47, on=k47, how="outer")
pp17 = wavg(pp, ["adm1_pcode", "adm1_name", "annee_depart", "annee_arrivee", "sexe", "cycle"]).pivot_table(
    index=["adm1_pcode", "adm1_name", "annee_depart", "annee_arrivee", "sexe"], columns="cycle", values="taux_abandon_publie").reset_index()
pp17.columns = [f"taux_abandon_{c}" if c in ("post_primaire", "secondaire") else c for c in pp17.columns]
r17 = r17.merge(pp17, on=["adm1_pcode", "adm1_name", "annee_depart", "annee_arrivee", "sexe"], how="outer")

pr.to_csv(out_path("03-transformation", "architect", "flux-primaire-45-anciennes-provinces"), sep=";", index=False, encoding="utf-8")
p47.to_csv(out_path("03-transformation", "architect", "indicateurs-decrochage-47-provinces"), sep=";", index=False, encoding="utf-8")
r17.to_csv(out_path("03-transformation", "architect", "indicateurs-decrochage-17-regions"), sep=";", index=False, encoding="utf-8")
nat.to_csv(out_path("03-transformation", "architect", "indicateurs-decrochage-national"), sep=";", index=False, encoding="utf-8")
print(p47.shape, r17.shape)
print(nat[nat.sexe == "T"][["annee_depart", "taux_abandon_dgess", "taux_sortie_nette", "taux_effet_fermetures", "taux_abandon_corrige"]].round(2).to_string(index=False))
