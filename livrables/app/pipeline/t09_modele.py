"""T09-T10-T12 - Modèle de prévision, fiabilité, test rétrospectif 2022-23, explication et typologie.

Cible : taux d'abandon du primaire (CP1-CM1, convention DGESS) de l'année t (transition t -> t+1),
par nouvelle province (47). Prévision faite à la rentrée t+1 avec les seules informations connues
à cette date (voir t08_facteurs.py).
Validation temporelle glissante : pour chaque année test Y (2015 à 2023), apprentissage sur les
années < Y uniquement. Modèles : reconduction de la dernière valeur connue (référence), régression
ridge, gradient boosting (HistGradientBoosting). Intervalles de prévision : quantiles empiriques des
erreurs hors échantillon des années antérieures (approche conforme).
Entrée : 03_transformation/*table-analyse-47-provinces*.csv ; sorties dans 04_analyse.
Usage : python t09_modele.py [--racine CHEMIN_BF_DATA_CHALLENGE]
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.stats import spearmanr
import shap

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[3])
ap.add_argument("--sortie", type=Path, default=None)
a = ap.parse_args()
ROOT = a.racine
OUT = a.sortie or (ROOT / "livrables" / "04_analyse")
OUT.mkdir(parents=True, exist_ok=True)
TEAM = "VIGIE-Ecole-Team"
def op(role, desc, ext="csv", v=1):
    return OUT / f"{TEAM}_04-analyse_D1_{role}_{desc}_v{v}.{ext}"

d = pd.read_csv(next((ROOT / "livrables" / "03_transformation").glob("*table-analyse-47-provinces*.csv")), sep=";")
d.loc[(d.an <= 2018) & d.pdi_pour_1000_hab.isna(), "pdi_pour_1000_hab"] = 0.0   # avant les relevés CONASUR (2020)
d = d.sort_values(["adm2_pcode", "an"])
for sx in ["filles", "garcons"]:   # dernière valeur connue par sexe (transition t-1 -> t)
    d[f"retard_taux_abandon_dgess_{sx}"] = d.groupby("adm2_pcode")[f"taux_abandon_dgess_{sx}"].shift(1)

FAMILLES = {
    "Inertie scolaire": ["retard_taux_abandon_dgess", "retard_taux_sortie_nette", "taux_redoublement_primaire"],
    "Insécurité et déplacements": ["acled_evenements_violence_12m_p100k", "acled_deces_violence_12m_p100k",
                                   "acled_evenements_civils_12m_p100k", "acled_ev_violence_3m_rentree",
                                   "acled_variation_violence", "pdi_pour_1000_hab", "retard_taux_effet_fermetures"],
    "Offre scolaire et distance": ["eleves_par_maitre", "eleves_par_salle", "part_eleves_plus_5km", "eleves_pour_1000_hab"],
    "Pauvreté et travail des enfants": ["rgph2019_incidence_pauvrete", "rgph2019_emploi_7_14ans", "rgph2019_hors_ecole_6_11ans",
                                        "rgph2019_hors_ecole_12_15ans", "rgph2019_alphabetisation_15_64ans",
                                        "rgph2019_electricite", "rgph2019_acte_naissance"],
    "Situation des filles": ["rgph2019_filles_17ans_deja_mariees", "part_filles_primaire", "rgph2019_parite_primaire"],
}
FEATS = [f for v in FAMILLES.values() for f in v]
FAM_OF = {f: k for k, v in FAMILLES.items() for f in v}
LIB = {
    "retard_taux_abandon_dgess": "abandon de l'année précédente", "retard_taux_sortie_nette": "sorties nettes de l'année précédente",
    "taux_redoublement_primaire": "taux de redoublement", "acled_evenements_violence_12m_p100k": "violences (12 mois, pour 100 000 hab.)",
    "acled_deces_violence_12m_p100k": "décès liés aux violences (12 mois)", "acled_evenements_civils_12m_p100k": "violences contre les civils (12 mois)",
    "acled_ev_violence_3m_rentree": "violences des 3 mois avant la rentrée", "acled_variation_violence": "hausse des violences sur un an",
    "pdi_pour_1000_hab": "déplacés internes pour 1 000 hab.", "retard_taux_effet_fermetures": "fermetures d'écoles de l'année précédente",
    "eleves_par_maitre": "élèves par maître", "eleves_par_salle": "élèves par salle de classe", "part_eleves_plus_5km": "élèves à plus de 5 km de l'école",
    "eleves_pour_1000_hab": "élèves pour 1 000 habitants", "rgph2019_incidence_pauvrete": "pauvreté monétaire (2019)",
    "rgph2019_emploi_7_14ans": "travail des enfants de 7-14 ans (2019)", "rgph2019_hors_ecole_6_11ans": "enfants de 6-11 ans hors de l'école (2019)",
    "rgph2019_hors_ecole_12_15ans": "enfants de 12-15 ans hors de l'école (2019)", "rgph2019_alphabetisation_15_64ans": "alphabétisation des adultes (2019)",
    "rgph2019_electricite": "accès à l'électricité (2019)", "rgph2019_acte_naissance": "enfants ayant un acte de naissance (2019)",
    "rgph2019_filles_17ans_deja_mariees": "filles mariées à 17 ans (2019)", "part_filles_primaire": "part des filles parmi les élèves",
    "rgph2019_parite_primaire": "parité filles-garçons au primaire (2019)",
}
STRUCT = [f for f in FEATS if f not in FAMILLES["Inertie scolaire"]]   # modèle « attendu selon le profil » (sans inertie)

def ridge(feats):
    return Pipeline([("prep", ColumnTransformer([("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                                                                   ("sc", StandardScaler())]), feats)])),
                     ("m", RidgeCV(alphas=np.logspace(-1, 3, 20)))])
def gbm():
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=250, min_samples_leaf=15,
                                         l2_regularization=1.0, random_state=0)

lab = d[~d.ligne_prevision.astype(bool) & d.taux_abandon_dgess.notna() & d.retard_taux_abandon_dgess.notna()].copy()
prev = d[d.ligne_prevision.astype(bool)].copy()

def run_cv(target, feats, tag, years=range(2015, 2024)):
    rows = []
    for Y in years:
        tr, te = lab[(lab.an < Y) & lab[target].notna()], lab[(lab.an == Y) & lab[target].notna()]
        if te.empty:
            continue
        out = te[["adm2_pcode", "adm2_name", "adm1_name", "an", "annee_depart", "effectif_cp1_cm1", target]].copy()
        out["pred_reconduction"] = te["retard_" + target] if "retard_" + target in te else te.retard_taux_abandon_dgess
        fs = [f for f in feats if tr[f].notna().sum() >= 10]      # variables observées dans l'apprentissage
        r = ridge(fs).fit(tr[fs], tr[target]); out["pred_ridge"] = r.predict(te[fs])
        g = gbm().fit(tr[fs], tr[target]); out["pred_gbm"] = g.predict(te[fs])
        out["modele_cible"] = tag
        rows.append(out.rename(columns={target: "observe"}))
    return pd.concat(rows, ignore_index=True)

def metrics(cv, models=("pred_reconduction", "pred_ridge", "pred_gbm")):
    res = []
    for Y, g in cv.groupby("an"):
        dropouts = g.observe * g.effectif_cp1_cm1 / 100
        k = max(1, round(0.1 * len(g)))
        top_obs = set(g.nlargest(k, "observe").adm2_pcode)
        for m_ in models:
            e = g[m_] - g.observe
            top_pred = g.nlargest(k, m_)
            res.append({"annee_test": Y, "modele": m_.replace("pred_", ""), "mae": e.abs().mean(), "rmse": np.sqrt((e ** 2).mean()),
                        "spearman": spearmanr(g[m_], g.observe).statistic,
                        "part_abandons_captee_top10pct": (top_pred.observe * top_pred.effectif_cp1_cm1 / 100).sum() / dropouts.sum(),
                        "rappel_top10pct": len(top_obs & set(top_pred.adm2_pcode)) / k})
    return pd.DataFrame(res)

cv = run_cv("taux_abandon_dgess", FEATS, "abandon_total")
met = metrics(cv)
summ = met.groupby("modele")[["mae", "rmse", "spearman", "part_abandons_captee_top10pct", "rappel_top10pct"]].mean()
best = summ.mae.idxmin()
best_col = "pred_" + best

# intervalles conformes par zone : quantile 80 % des erreurs absolues hors échantillon des années
# antérieures, calculé séparément pour les zones à fort et faible défi sécuritaire (erreurs très différentes)
cv = cv.merge(lab[["adm2_pcode", "an", "acled_evenements_violence_12m_p100k"]], on=["adm2_pcode", "an"], how="left").sort_values("an")
ZONE = lambda x: np.where(x >= 5, "fort", "faible")
cv["zone_securite"] = ZONE(cv.acled_evenements_violence_12m_p100k)
cov = []
for Y in sorted(cv.an.unique()):
    past = cv[(cv.an < Y) & (cv.an >= Y - 3)]     # fenêtre glissante : erreurs des 3 dernières années
    if past.an.nunique() < 2:
        continue
    for z in ["fort", "faible"]:
        pz = past[past.zone_securite == z]
        cur = cv[(cv.an == Y) & (cv.zone_securite == z)]
        if len(pz) < 10 or cur.empty:
            continue
        q = np.quantile((pz[best_col] - pz.observe).abs(), 0.8)
        cov.append({"annee_test": Y, "zone_securite": z, "demi_largeur_80": q, "n": len(cur),
                    "couverture": ((cur[best_col] - cur.observe).abs() <= q).mean()})
cov = pd.DataFrame(cov)
q80z = {z: np.quantile((g[best_col] - g.observe).abs(), 0.8) for z, g in cv[cv.an >= cv.an.max() - 2].groupby("zone_securite")}
q80 = np.quantile((cv[best_col] - cv.observe).abs(), 0.8)

# calibration par déciles de prévision
cv["decile"] = pd.qcut(cv[best_col], 10, labels=False, duplicates="drop")
calib = cv.groupby("decile").agg(prevision_moyenne=(best_col, "mean"), observe_moyen=("observe", "mean"), n=("observe", "size")).reset_index()

# équité : filles / garçons, zones à fort défi sécuritaire, villes
cvF = run_cv("taux_abandon_dgess_filles", FEATS + ["retard_taux_abandon_dgess_filles"], "filles")
cvG = run_cv("taux_abandon_dgess_garcons", FEATS + ["retard_taux_abandon_dgess_garcons"], "garcons")
eq = []
for nm, c_ in [("filles", cvF), ("garçons", cvG)]:
    eq.append({"groupe": nm, "mae": (c_[best_col] - c_.observe).abs().mean(), "biais_moyen": (c_[best_col] - c_.observe).mean(), "n": len(c_)})
cvx = cv.copy()
cvx["zone"] = np.where(cvx.acled_evenements_violence_12m_p100k >= 5, "fort défi sécuritaire (≥ 5 violences / 100 000 hab. / an)", "défi sécuritaire faible")
cvx.loc[cvx.adm2_pcode.isin(["BF1300", "BF5301"]), "zone"] = "grandes villes (Kadiogo, Houet)"
for z, g in cvx.groupby("zone"):
    eq.append({"groupe": z, "mae": (g[best_col] - g.observe).abs().mean(), "biais_moyen": (g[best_col] - g.observe).mean(), "n": len(g)})
eq = pd.DataFrame(eq)

# T10 - test rétrospectif 2021-22 (pic de fermetures) : le modèle, entraîné jusqu'en 2020, l'aurait-il vu ?
ret = cv[cv.an == 2021].copy()
k = round(0.1 * len(ret))
retro = {"annee": "2021-22 (abandon mesuré par l'annuaire 2022-23)",
         "abandon_national_observe": float((ret.observe * ret.effectif_cp1_cm1).sum() / ret.effectif_cp1_cm1.sum()),
         "abandon_national_prevu_modele": float((ret[best_col] * ret.effectif_cp1_cm1).sum() / ret.effectif_cp1_cm1.sum()),
         "abandon_national_prevu_reconduction": float((ret.pred_reconduction * ret.effectif_cp1_cm1).sum() / ret.effectif_cp1_cm1.sum()),
         "provinces_top10_observees": sorted(ret.nlargest(k, "observe").adm2_name),
         "provinces_top10_prevues_modele": sorted(ret.nlargest(k, best_col).adm2_name),
         "provinces_top10_prevues_reconduction": sorted(ret.nlargest(k, "pred_reconduction").adm2_name)}
retro["rappel_modele"] = len(set(retro["provinces_top10_observees"]) & set(retro["provinces_top10_prevues_modele"])) / k
retro["rappel_reconduction"] = len(set(retro["provinces_top10_observees"]) & set(retro["provinces_top10_prevues_reconduction"])) / k

# modèle final, prévision 2024-25 et explication
final_g = gbm().fit(lab[FEATS], lab.taux_abandon_dgess)
final_r = ridge(FEATS).fit(lab[FEATS], lab.taux_abandon_dgess)
prev["prevision_gbm"] = final_g.predict(prev[FEATS])
prev["prevision_ridge"] = final_r.predict(prev[FEATS])
prev["prevision_reconduction"] = prev.retard_taux_abandon_dgess
prev["prevision"] = prev[{"gbm": "prevision_gbm", "ridge": "prevision_ridge", "reconduction": "prevision_reconduction"}[best]].clip(lower=0)
prev["zone_securite"] = ZONE(prev.acled_evenements_violence_12m_p100k)
prev["demi_largeur"] = prev.zone_securite.map(q80z)
prev["intervalle_80_bas"] = (prev.prevision - prev.demi_largeur).clip(lower=0)
prev["intervalle_80_haut"] = prev.prevision + prev.demi_largeur

# effectifs 2024-25 (CP1-CM1) par nouvelle province pour les décrocheurs attendus
cons = pd.read_csv(next((ROOT / "livrables" / "02_nettoyage").glob("*effectifs-primaire-provinces-consolide_v2.csv")), sep=";")
W = pd.read_csv(next((ROOT / "livrables" / "01_collecte").glob("*passage-anciennes-provinces*")), sep=";")
e24 = cons[(cons.annee_scolaire == "2024/2025") & (cons.sexe == "T") & cons.niveau.isin(["CP1", "CP2", "CE1", "CE2", "CM1"])]
e24 = e24.groupby("old_adm2_pcode").effectif.sum().reset_index().merge(W, on="old_adm2_pcode")
e24 = (e24.effectif * e24.poids_pop_2019).groupby(e24.adm2_pcode).sum().rename("effectif_cp1_cm1_2024")
prev = prev.merge(e24, left_on="adm2_pcode", right_index=True, how="left")
prev["decrocheurs_attendus"] = prev.prevision / 100 * prev.effectif_cp1_cm1_2024

# écart au risque attendu (dernière année observée, modèle structurel sans inertie)
st = ridge(STRUCT).fit(lab[lab.an < lab.an.max()][STRUCT], lab[lab.an < lab.an.max()].taux_abandon_dgess)
lastY = lab[lab.an == lab.an.max()].copy()
lastY["attendu_selon_profil"] = st.predict(lastY[STRUCT])
lastY["ecart_au_risque_attendu"] = lastY.taux_abandon_dgess - lastY.attendu_selon_profil
prev = prev.merge(lastY[["adm2_pcode", "taux_abandon_dgess", "taux_abandon_corrige", "attendu_selon_profil", "ecart_au_risque_attendu"]].rename(
    columns={"taux_abandon_dgess": "abandon_observe_2023_24", "taux_abandon_corrige": "abandon_corrige_2023_24"}), on="adm2_pcode", how="left")
seuil_rouge, seuil_orange = np.quantile(prev.prevision, 0.8), np.quantile(prev.prevision, 0.5)
prev["niveau_alerte"] = np.select([prev.prevision >= seuil_rouge, prev.prevision >= seuil_orange], ["rouge", "orange"], "jaune")

# SHAP (modèle gradient boosting final) sur les lignes de prévision
expl = shap.TreeExplainer(final_g)
sv = expl.shap_values(prev[FEATS])
S = pd.DataFrame(sv, columns=FEATS, index=prev.adm2_pcode)
shap_long = S.reset_index().melt(id_vars="adm2_pcode", var_name="facteur", value_name="contribution_points")
shap_long["famille"] = shap_long.facteur.map(FAM_OF)
shap_long["libelle"] = shap_long.facteur.map(LIB)
shap_long = shap_long.merge(prev[["adm2_pcode", "adm2_name", "adm1_name"]], on="adm2_pcode")
fam = shap_long.groupby(["adm2_pcode", "famille"]).contribution_points.sum().unstack()
pos = fam.clip(lower=0)
prev["cause_dominante"] = prev.adm2_pcode.map(pos.idxmax(axis=1).where(pos.max(axis=1) > 0, "aucune cause au-dessus de la moyenne"))
top3 = (shap_long[shap_long.contribution_points > 0].sort_values("contribution_points", ascending=False)
        .groupby("adm2_pcode").head(3).groupby("adm2_pcode").libelle.apply(lambda s: " ; ".join(s)))
prev["trois_facteurs_principaux"] = prev.adm2_pcode.map(top3)
glob_imp = (pd.DataFrame(np.abs(expl.shap_values(lab[FEATS])), columns=FEATS).mean().sort_values(ascending=False)
            .rename("shap_moyen_absolu_points").reset_index().rename(columns={"index": "facteur"}))
glob_imp["libelle"] = glob_imp.facteur.map(LIB); glob_imp["famille"] = glob_imp.facteur.map(FAM_OF)

# typologie des 17 régions : profil des contributions par famille (moyenne pondérée par les effectifs)
fr = fam.join(prev.set_index("adm2_pcode")[["adm1_name", "effectif_cp1_cm1_2024"]])
reg = fr.groupby("adm1_name").apply(lambda g: pd.Series({c: np.average(g[c], weights=g.effectif_cp1_cm1_2024) for c in fam.columns}), include_groups=False)
Z = (reg - reg.mean()) / reg.std(ddof=0)
km = KMeans(n_clusters=4, n_init=50, random_state=0).fit(Z)
reg["groupe"] = km.labels_
names = {}
for gid in range(4):
    c_ = pd.Series(km.cluster_centers_[gid], index=fam.columns).sort_values(ascending=False)
    names[gid] = "Dominante : " + c_.index[0].lower() + (" et " + c_.index[1].lower() if c_.iloc[1] > 0.5 else "")
reg["profil_regional"] = reg.groupe.map(names)
reg = reg.reset_index()

# post-primaire : référence par reconduction (peu d'années), erreur hors échantillon
pp = lab[lab.taux_abandon_post_primaire.notna() & lab.retard_taux_abandon_post_primaire.notna()]
pp_mae = float((pp.taux_abandon_post_primaire - pp.retard_taux_abandon_post_primaire).abs().mean()) if len(pp) else None

# --- écriture ---
cv.drop(columns=["decile"]).to_csv(op("scientist", "previsions-hors-echantillon-2015-2023"), sep=";", index=False)
met.to_csv(op("scientist", "fiabilite-par-annee-test"), sep=";", index=False)
summ.reset_index().to_csv(op("scientist", "fiabilite-synthese-modeles"), sep=";", index=False)
cov.to_csv(op("scientist", "couverture-intervalles-80"), sep=";", index=False)
calib.to_csv(op("scientist", "calibration-deciles"), sep=";", index=False)
eq.to_csv(op("scientist", "equite-erreurs-par-groupe"), sep=";", index=False)
prev_cols = ["adm1_pcode", "adm1_name", "adm2_pcode", "adm2_name", "annee_depart", "prevision", "intervalle_80_bas", "intervalle_80_haut",
             "prevision_gbm", "prevision_ridge", "prevision_reconduction", "niveau_alerte", "effectif_cp1_cm1_2024", "decrocheurs_attendus",
             "abandon_observe_2023_24", "abandon_corrige_2023_24", "attendu_selon_profil", "ecart_au_risque_attendu",
             "cause_dominante", "trois_facteurs_principaux", "zone_securite", "acled_evenements_violence_12m_p100k", "pdi_pour_1000_hab"]
prev[prev_cols].sort_values("prevision", ascending=False).to_csv(op("scientist", "prevision-abandon-primaire-2024-25-47-provinces"), sep=";", index=False)
shap_long.to_csv(op("scientist", "explication-facteurs-shap-47-provinces"), sep=";", index=False)
glob_imp.to_csv(op("scientist", "importance-globale-facteurs"), sep=";", index=False)
reg.to_csv(op("analyst", "typologie-17-regions"), sep=";", index=False)
bilan = {"modele_retenu": best, "mae_points_par_modele": summ.mae.round(3).to_dict(),
         "gain_mae_vs_reconduction_pct": round(100 * (1 - summ.mae[best] / summ.mae["reconduction"]), 1),
         "spearman_par_modele": summ.spearman.round(3).to_dict(),
         "part_abandons_captee_top10pct": summ.part_abandons_captee_top10pct.round(3).to_dict(),
         "rappel_top10pct": summ.rappel_top10pct.round(3).to_dict(),
         "intervalle_80_demi_largeur_points_par_zone": {k: round(float(v), 2) for k, v in q80z.items()}, "couverture_80_moyenne": round(float(np.average(cov.couverture, weights=cov.n)), 3),
         "test_retrospectif_2021_22": retro, "post_primaire_mae_reconduction_points": pp_mae,
         "seuils_alerte": {"rouge": round(float(seuil_rouge), 2), "orange": round(float(seuil_orange), 2)},
         "erreur_mediane_points_par_zone_gbm": (cv.assign(e=(cv.pred_gbm - cv.observe).abs()).groupby("zone_securite").e.median().round(2).to_dict()),
         "erreur_moyenne_points_par_zone_gbm": (cv.assign(e=(cv.pred_gbm - cv.observe).abs()).groupby("zone_securite").e.mean().round(2).to_dict()),
         "mae_ponderee_effectifs_gbm": round(float(np.average((cv.pred_gbm - cv.observe).abs(), weights=cv.effectif_cp1_cm1)), 2),
         "n_lignes_apprentissage": int(len(lab)), "annees_test": sorted(int(x) for x in cv.an.unique())}
json.dump(bilan, open(op("scientist", "bilan-modele", "json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
print(json.dumps(bilan, ensure_ascii=False, indent=1, default=str))
print(eq.round(2).to_string(index=False))
print(reg[["adm1_name", "profil_regional"]].to_string(index=False))
