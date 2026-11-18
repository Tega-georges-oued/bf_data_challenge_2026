"""T08 - Table d'analyse : une ligne par nouvelle province (47) et par transition t -> t+1.

Règle de disponibilité : la prévision de l'abandon pendant l'année t (mesuré par l'annuaire t+1) est
faite à la rentrée t+1 (octobre). Seules les informations connues à cette date sont utilisées :
  - abandon de t-1 -> t (annuaire t, publié vers juillet t+1)  [retard_*]
  - moyens de l'année t (écoles, maîtres, salles), redoublement et part des filles en t
  - fermetures / réouvertures d'écoles entre t-1 et t
  - violences ACLED d'octobre t à septembre t+1 (12 mois) et de juillet à septembre t+1 (3 mois)
  - déplacés internes (CONASUR) au dernier relevé publié avant octobre t+1, pour 1 000 habitants
  - contexte 2019 (RGPH) : pauvreté, enfants hors de l'école, travail des enfants, mariage précoce,
    distance à l'école (annuaire t)
Cible : taux d'abandon de t -> t+1 (convention DGESS, et corrigé des fermetures).
Sources ACLED, pauvreté, vulnérabilités, déplacés, distances : extractions contrôlées (livrables/02_nettoyage/extractions_sources_20261116 ; scripts : livrables/app/pipeline/extractions_sources).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import ROOT, DATAS, out_path

CG = Path(__file__).resolve().parents[2] / "02_nettoyage" / "extractions_sources_20261116"
W = pd.read_csv(next((ROOT / "livrables" / "01_collecte").glob("*passage-anciennes-provinces*")), sep=";")
COM = pd.read_csv(next((ROOT / "livrables" / "01_collecte").glob("*referentiel-communes*")), sep=";")
POP47 = COM.groupby("adm2_pcode").pop_2019.sum()
ind = pd.read_csv(next((ROOT / "livrables" / "03_transformation").glob("*indicateurs-decrochage-47-provinces*")), sep=";")
T = ind[ind.sexe == "T"].copy()
F_ = ind[ind.sexe == "F"][["adm2_pcode", "annee_depart", "taux_abandon_dgess", "taux_abandon_corrige"]].rename(
    columns={"taux_abandon_dgess": "taux_abandon_dgess_filles", "taux_abandon_corrige": "taux_abandon_corrige_filles"})
G_ = ind[ind.sexe == "G"][["adm2_pcode", "annee_depart", "taux_abandon_dgess", "taux_abandon_corrige"]].rename(
    columns={"taux_abandon_dgess": "taux_abandon_dgess_garcons", "taux_abandon_corrige": "taux_abandon_corrige_garcons"})
d = T.merge(F_, on=["adm2_pcode", "annee_depart"], how="left").merge(G_, on=["adm2_pcode", "annee_depart"], how="left")
d["an"] = d.annee_depart.str[:4].astype(int)
# ligne de prévision : abandon pendant 2024-25 (mesuré par l'annuaire 2025-26, non publié) -> cible inconnue
last = int(d.an.max()) + 1
prev = d[d.an == last - 1][["adm1_pcode", "adm1_name", "adm2_pcode", "adm2_name"]].copy()
prev["an"] = last
prev["annee_depart"] = f"{last}/{last + 1}"
prev["annee_arrivee"] = f"{last + 1}/{last + 2}"
prev["sexe"] = "T"
prev["ligne_prevision"] = True
d["ligne_prevision"] = False
d = pd.concat([d, prev], ignore_index=True)

# retards (valeur connue à la rentrée t+1 : transition t-1 -> t)
lag = d[["adm2_pcode", "an", "taux_abandon_dgess", "taux_abandon_corrige", "taux_sortie_nette", "taux_effet_fermetures",
         "taux_abandon_post_primaire", "taux_abandon_secondaire"]].copy()
lag["an"] += 1
lag = lag.rename(columns={c: "retard_" + c for c in lag.columns if c.startswith("taux")})
d = d.merge(lag, on=["adm2_pcode", "an"], how="left")

# moyens et structure de l'année t (anciennes provinces -> 47 par poids de population)
cons = pd.read_csv(next((ROOT / "livrables" / "02_nettoyage").glob("*effectifs-primaire-provinces-consolide_v2.csv")), sep=";")
tt = cons[cons.niveau == "TOTAL"].pivot_table(index=["old_adm2_pcode", "annee_scolaire"], columns="sexe", values=["effectif", "redoublants"]).reset_index()
tt.columns = ["old_adm2_pcode", "annee_scolaire", "eff_F", "eff_G", "eff_T", "red_F", "red_G", "red_T"]
res = pd.read_csv(next((ROOT / "livrables" / "02_nettoyage").glob("*ressources-primaire-provinces*")), sep=";")
tt = tt.merge(res[["old_adm2_pcode", "annee_scolaire", "ecoles", "maitres_charges_cours", "salles_classe"]], on=["old_adm2_pcode", "annee_scolaire"], how="left")
tt = tt.merge(W[["old_adm2_pcode", "adm2_pcode", "poids_pop_2019"]], on="old_adm2_pcode")
num = ["eff_F", "eff_G", "eff_T", "red_T", "ecoles", "maitres_charges_cours", "salles_classe"]
for c_ in num:
    tt[c_] = tt[c_] * tt.poids_pop_2019
m = tt.groupby(["adm2_pcode", "annee_scolaire"], as_index=False)[num].sum(min_count=1)
m["part_filles_primaire"] = 100 * m.eff_F / m.eff_T
m["taux_redoublement_primaire"] = 100 * m.red_T / m.eff_T
m["eleves_par_maitre"] = m.eff_T / m.maitres_charges_cours
m["eleves_par_salle"] = m.eff_T / m.salles_classe
m["eleves_pour_1000_hab"] = 1000 * m.eff_T / m.adm2_pcode.map(POP47)
d = d.merge(m[["adm2_pcode", "annee_scolaire", "part_filles_primaire", "taux_redoublement_primaire", "eleves_par_maitre",
               "eleves_par_salle", "eleves_pour_1000_hab"]].rename(columns={"annee_scolaire": "annee_depart"}), on=["adm2_pcode", "annee_depart"], how="left")

# ACLED (anciennes provinces, mois) -> fenêtres octobre t .. septembre t+1
ac = pd.read_csv(CG / "acled_provinces_mois_signaux.csv", sep=";")
ac["date"] = pd.to_datetime(ac.mois + "-01")
ac = ac.merge(W[["old_adm2_pcode", "adm2_pcode", "poids_pop_2019"]], on="old_adm2_pcode")
ac["ev"] = ac.evenements * ac.poids_pop_2019
ac["dc"] = ac.deces * ac.poids_pop_2019
rows = []
for an in sorted(d.an.unique()):
    w12 = ac[(ac.date >= f"{an}-10-01") & (ac.date <= f"{an + 1}-09-01")]
    w3 = ac[(ac.date >= f"{an + 1}-07-01") & (ac.date <= f"{an + 1}-09-01")]
    wp = ac[(ac.date >= f"{an - 1}-10-01") & (ac.date <= f"{an}-09-01")]
    g12 = w12.groupby(["adm2_pcode", "categorie"])[["ev", "dc"]].sum().unstack()
    g12.columns = [f"acled_{a}_{b}_12m" for a, b in g12.columns]
    g3 = w3[w3.categorie == "violence_politique"].groupby("adm2_pcode").ev.sum().rename("acled_ev_violence_3m_rentree")
    gp = wp[wp.categorie == "violence_politique"].groupby("adm2_pcode").ev.sum().rename("acled_ev_violence_12m_precedents")
    g = pd.concat([g12, g3, gp], axis=1).reset_index().rename(columns={"index": "adm2_pcode"})
    g["an"] = an
    rows.append(g)
acf = pd.concat(rows).fillna(0)
acf = acf.rename(columns={"acled_ev_violence_politique_12m": "acled_evenements_violence_12m", "acled_dc_violence_politique_12m": "acled_deces_violence_12m",
                          "acled_ev_ciblage_civils_12m": "acled_evenements_civils_12m", "acled_dc_ciblage_civils_12m": "acled_deces_civils_12m"})
acf["acled_variation_violence"] = acf.acled_evenements_violence_12m - acf.acled_ev_violence_12m_precedents
d = d.merge(acf, on=["adm2_pcode", "an"], how="left")
for c_ in [c for c in d.columns if c.startswith("acled_")]:
    d[c_] = d[c_].fillna(0)
for c_ in ["acled_evenements_violence_12m", "acled_deces_violence_12m", "acled_evenements_civils_12m"]:
    d[c_ + "_p100k"] = 1e5 * d[c_] / d.adm2_pcode.map(POP47)

# déplacés internes : dernier relevé publié avant octobre t+1 (couverture partielle signalée)
pdi = pd.read_csv(CG / "pdi_47_provinces_couverture_explicitee.csv", sep=";")
pdi["date"] = pd.to_datetime(pdi.date)
vals = []
for an in sorted(d.an.unique()):
    x = pdi[pdi.date < f"{an + 1}-10-01"]
    if x.empty:
        continue
    last = x[x.date == x.date.max()]
    vals.append(pd.DataFrame({"adm2_pcode": last.adm2_pcode, "an": an, "pdi_pour_1000_hab": 1000 * last.pdi_dans_communes_renseignees / last.adm2_pcode.map(POP47),
                              "pdi_couverture_communes": last.couverture_communes, "pdi_date_releve": last.date.dt.strftime("%Y-%m-%d")}))
d = d.merge(pd.concat(vals), on=["adm2_pcode", "an"], how="left")

# contexte 2019 (RGPH 2019, communes -> provinces pondérées par la population)
vul = pd.read_csv(CG / "rgph2019_vulnerabilites_351_communes.csv", sep=";")
vcols = ["hors_ecole_6_11ans", "hors_ecole_12_15ans", "emploi_7_14ans", "filles_17ans_deja_mariees", "alphabetisation_15_64ans",
         "electricite", "acte_naissance", "parite_primaire", "frequentation_nette_postprimaire"]
vul = vul.merge(COM[["adm3_pcode", "pop_2019"]], on="adm3_pcode")
v = vul.groupby("adm2_pcode").apply(lambda g: pd.Series({c_: np.average(g[c_].dropna(), weights=g.loc[g[c_].notna(), "pop_2019"]) if g[c_].notna().any() else np.nan for c_ in vcols}), include_groups=False).reset_index()
v.columns = ["adm2_pcode"] + [f"rgph2019_{c_}" for c_ in vcols]
pv = pd.read_csv(CG / "pauvrete_monetaire_47_provinces_recomposee.csv", sep=";")[["adm2_pcode", "incidence_pauvrete_estimee"]].rename(
    columns={"incidence_pauvrete_estimee": "rgph2019_incidence_pauvrete"})
d = d.merge(v, on="adm2_pcode", how="left").merge(pv, on="adm2_pcode", how="left")

# distance à l'école (part des élèves à plus de 5 km, public + privé, annuaire t)
ds = pd.read_csv(CG / "distances_eleves_provinces_long.csv", sep=";")
ds = ds[(ds.perimetre == "public_prive") & ds.eligible_analyse]
dd = ds.pivot_table(index=["old_adm2_pcode", "annee_scolaire"], columns="variable", values="valeur").reset_index()
dd = dd.merge(W[["old_adm2_pcode", "adm2_pcode", "poids_pop_2019"]], on="old_adm2_pcode")
dd["n5"] = dd.part_trajet_plus_5km * dd.eleves_denominateur * dd.poids_pop_2019
dd["den"] = dd.eleves_denominateur * dd.poids_pop_2019
dd = dd.groupby(["adm2_pcode", "annee_scolaire"], as_index=False)[["n5", "den"]].sum()
dd["part_eleves_plus_5km"] = dd.n5 / dd.den
d = d.merge(dd[["adm2_pcode", "annee_scolaire", "part_eleves_plus_5km"]].rename(columns={"annee_scolaire": "annee_depart"}), on=["adm2_pcode", "annee_depart"], how="left")

d = d.sort_values(["adm2_pcode", "an"])
f = out_path("03-transformation", "architect", "table-analyse-47-provinces")
d.to_csv(f, sep=";", index=False, encoding="utf-8")
print(f.name, d.shape)
print(d.isna().mean().round(2)[d.isna().mean() > 0].to_string())
