"""L03 schéma des données, L05 plan du parcours (03_transformation) et L06 rapport de fiabilité (04_analyse).

Usage : python t15b_schema_parcours_fiabilite.py [--racine CHEMIN_BF_DATA_CHALLENGE]
PDF générés directement avec ReportLab (dépendance Python) ; les diagrammes sont dans livrables/app/pipeline/diagrammes.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_outils import nouveau, para, puces, tableau, image, enregistrer

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[3])
ROOT = ap.parse_args().racine
DIAG = Path(__file__).resolve().parent / "diagrammes"
TEAM = "VIGIE-Ecole-Team"
def latest(folder, pat):
    return sorted((ROOT / "livrables" / folder).glob(f"*{pat}*"))[-1]
def fr(x):
    return str(x).replace(".", ",")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

# ---------------- L03 schéma ----------------
d = nouveau("Schéma des données", "Dépôt 03_transformation · rôle : architect · VIGIE-École")
para(d, "La base est organisée autour de deux clés : le code de province (adm2_pcode, 47 provinces du découpage 2025) et "
        "l'année scolaire de départ (annee_depart : l'abandon de l'année t est mesuré par l'annuaire t+1). Les annuaires étant "
        "publiés sur les 45 anciennes provinces, les flux sont d'abord calculés sur ces 45 provinces (old_adm2_pcode), puis "
        "reportés sur les 47 provinces par la table de passage, construite à partir des 351 communes.")
image(d, DIAG / "schema.png", 13.5, "Figure 1. Tables, clés et relations (PK : clé primaire).")
rows = []
for folder in ["01_collecte", "02_nettoyage", "03_transformation"]:
    for f in sorted((ROOT / "livrables" / folder).glob("*.csv")):
        if "dictionnaire" in f.name or "registre" in f.name:
            continue
        try:
            x = pd.read_csv(f, sep=";", low_memory=False)
        except Exception:
            continue
        cles = [c for c in ["adm3_pcode", "old_adm2_pcode", "adm2_pcode", "adm1_pcode", "annee_scolaire", "annee_depart", "an", "niveau", "sexe"] if c in x.columns]
        rows.append([f.name.replace(TEAM + "_", ""), f"{len(x):,}".replace(",", " "), len(x.columns), ", ".join(cles)])
d.add_heading("Tables et clés", 2)
tableau(d, ["Fichier", "Lignes", "Colonnes", "Clés"], rows, [9, 1.6, 1.6, 5], taille=7)
d.add_heading("Règles d'intégrité vérifiées", 2)
puces(d, ["Référentiel : 351 communes, population 2019 totale 20 505 155, identique au chiffre officiel du RGPH 2019.",
          "Passage 45 → 47 provinces : les poids d'une ancienne province somment à 1 ; seules Soum (Djelgodji 65,58 %, Karo-Peli 34,42 %) et "
          "Tapoa (Dyamongou 31,47 %, Gobnangou 68,53 %) sont réparties.",
          "Effectifs : filles + garçons = total, sauf Oubritenga 2010-11 (7 cases signalées dans le journal) ; totaux régionaux comparés "
          "à la base principale (387 cases sur 390 identiques).",
          "Indicateurs : la somme des 47 provinces redonne les 17 régions et le total national."])
p = ROOT / "livrables" / "03_transformation" / f"{TEAM}_03-transformation_D1_architect_schema-donnees_v1.docx"
if enregistrer(d, p): p.unlink()

# ---------------- L05 parcours ----------------
d = nouveau("Plan du parcours des données", "Dépôt 03_transformation · rôle : architect · des sources à l'application")
image(d, DIAG / "parcours.png", 17, "Figure 1. Des sources aux cinq dépôts et à l'application.")
etapes = [
 ["1. Collecte", "01_collecte", "t02_referentiel.py, t03_registre_sources.py", "Référentiel 17 régions / 47 provinces / 351 communes ; registre de 248 fichiers (MD5)"],
 ["2. Nettoyage", "02_nettoyage", "t04_primaire.py, t04b_consolider_primaire.py", "Effectifs du primaire 2008-09 à 2024-25 par ancienne province, niveau et sexe ; écoles, maîtres, salles ; journaux"],
 ["3. Transformation", "03_transformation", "t07_indicateurs.py, t08_facteurs.py", "Flux de cohorte, abandon publié et corrigé (47 provinces, 17 régions, national) ; table d'analyse avec les facteurs"],
 ["4. Analyse", "04_analyse", "t09_modele.py", "Validation 2015-2023, prévision 2024-25 avec intervalles, explication SHAP, typologie, équité"],
 ["5. Interprétation", "05_interpretation, app", "t14_fiches_atlas.py, livrables/app/app.py", "Fiches des 17 régions, atlas, application VIGIE-École, documentation"],
]
tableau(d, ["Étape", "Dépôt", "Script", "Produit"], etapes, [2.6, 3, 4.8, 7], taille=7.5)
d.add_heading("Règle de disponibilité de l'information", 2)
para(d, "Chaque variable de la prévision doit être connue à la rentrée d'octobre de l'année t+1, quand l'abandon de l'année t "
        "n'est pas encore publié. Sont donc utilisés : le taux d'abandon de t-1, les ressources de l'année t, les événements ACLED "
        "d'octobre t à septembre t+1 et ceux de juillet à septembre t+1, le dernier relevé des personnes déplacées avant octobre t+1, "
        "le contexte du RGPH 2019 (fixe) et les distances domicile-école de l'année t.")
d.add_heading("Trois vitesses de mise à jour", 2)
puces(d, [("Annuelle : ", "nouvel annuaire DGESS → relancer les étapes 2 à 5 (une commande, voir la documentation, partie 7)."),
          ("Mensuelle : ", "ACLED et CONASUR → mettre à jour la table d'analyse et la prévision de l'année en cours."),
          ("Fixe : ", "RGPH 2019 et limites administratives, jusqu'au prochain recensement ou découpage.")])
p = ROOT / "livrables" / "03_transformation" / f"{TEAM}_03-transformation_D1_architect_parcours-donnees_v1.docx"
if enregistrer(d, p): p.unlink()

# ---------------- L06 fiabilité ----------------
B = json.load(open(latest("04_analyse", "bilan-modele"), encoding="utf-8"))
fi = pd.read_csv(latest("04_analyse", "fiabilite-par-annee-test"), sep=";")
sy = pd.read_csv(latest("04_analyse", "fiabilite-synthese-modeles"), sep=";")
ca = pd.read_csv(latest("04_analyse", "calibration-deciles"), sep=";")
cv = pd.read_csv(latest("04_analyse", "couverture-intervalles-80"), sep=";")
eq = pd.read_csv(latest("04_analyse", "equite-erreurs-par-groupe"), sep=";")
tmp = ROOT / "livrables" / "04_analyse" / "_fig"; tmp.mkdir(exist_ok=True)
NOM = {"gbm": "Gradient boosting (retenu)", "ridge": "Régression ridge", "reconduction": "Reconduction (référence)"}
fig, ax = plt.subplots(figsize=(7, 3))
for m, c in [("gbm", "#c0392b"), ("ridge", "#7f8c8d"), ("reconduction", "#2c3e50")]:
    s = fi[fi.modele == m]; ax.plot(s.annee_test, s.mae, "-o", ms=3, color=c, label=NOM[m])
ax.set_xlabel("Année prévue (abandon de l'année t)"); ax.set_ylabel("Erreur absolue moyenne (points)")
ax.grid(alpha=.3); ax.legend(frameon=False, fontsize=8); ax.spines[["top", "right"]].set_visible(False)
fig.savefig(tmp / "mae.png", dpi=180, bbox_inches="tight"); plt.close(fig)
fig, axs = plt.subplots(1, 2, figsize=(7.5, 3))
axs[0].plot(ca.prevision_moyenne, ca.observe_moyen, "o-", color="#c0392b"); mx = max(ca.prevision_moyenne.max(), ca.observe_moyen.max())
axs[0].plot([0, mx], [0, mx], "--", color="grey"); axs[0].set_xlabel("Prévu (%)"); axs[0].set_ylabel("Observé (%)"); axs[0].set_title("Calibration par décile", fontsize=9)
for z, c in [("faible", "#2c3e50"), ("fort", "#c0392b")]:
    s = cv[cv.zone_securite == z]; axs[1].plot(s.annee_test, s.couverture * 100, "-o", ms=3, color=c, label=f"défi sécuritaire {z}")
axs[1].axhline(80, ls="--", color="grey"); axs[1].set_ylim(0, 105); axs[1].set_title("Couverture des intervalles à 80 %", fontsize=9)
axs[1].legend(frameon=False, fontsize=7); axs[1].set_ylabel("%")
for a in axs: a.grid(alpha=.3); a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(tmp / "calib.png", dpi=180, bbox_inches="tight"); plt.close(fig)

d = nouveau("Rapport de fiabilité du modèle", "Dépôt 04_analyse · rôle : scientist · prévision de l'abandon au primaire par province")
em, mm_ = B["erreur_mediane_points_par_zone_gbm"], B["erreur_moyenne_points_par_zone_gbm"]
r = B["test_retrospectif_2021_22"]
d.add_heading("En bref", 2)
puces(d, [f"Le modèle retenu (gradient boosting) réduit l'erreur de {fr(B['gain_mae_vs_reconduction_pct'])} % par rapport à la simple reconduction "
          f"du taux de l'année précédente ({fr(B['mae_points_par_modele']['gbm'])} contre {fr(B['mae_points_par_modele']['reconduction'])} points en moyenne).",
          f"Il classe mieux les provinces : corrélation de rang {fr(B['spearman_par_modele']['gbm'])} contre {fr(B['spearman_par_modele']['reconduction'])} ; "
          f"il retrouve {B['rappel_top10pct']['gbm']*100:.0f} % des provinces du top 10 % contre {B['rappel_top10pct']['reconduction']*100:.0f} %.",
          f"L'erreur dépend du contexte : erreur médiane de {fr(em['faible'])} points dans les zones à faible défi sécuritaire, {fr(em['fort'])} points dans "
          f"les zones à fort défi sécuritaire (moyennes : {fr(mm_['faible'])} et {fr(mm_['fort'])}). Pondérée par les effectifs : {fr(B['mae_ponderee_effectifs_gbm'])} points.",
          "Les grandes erreurs viennent des fermetures massives d'écoles (Sahel 2017-18, puis 2020-21 et 2021-22), qui font sortir jusqu'à la totalité "
          "des élèves d'une province en un an. Aucune donnée publique disponible à la rentrée ne permet de les prévoir. Dans ces zones, la prévision sert "
          "à classer les provinces, pas à donner un chiffre exact."])
d.add_heading("Protocole", 2)
para(d, f"Validation temporelle glissante : pour chaque année de {min(B['annees_test'])} à {max(B['annees_test'])}, le modèle est entraîné sur les "
        f"seules années antérieures puis prévoit l'année suivante, avec les variables connues à la rentrée ({B['n_lignes_apprentissage']} lignes "
        "province-année au total). Trois modèles sont comparés : la reconduction du taux de l'année précédente (référence), une régression ridge et un "
        "gradient boosting (HistGradientBoosting, profondeur 3, 250 itérations, taux d'apprentissage 0,05). Les intervalles à 80 % sont conformes : "
        "leur largeur est le 80e centile des erreurs des trois années précédentes, calculé séparément pour les zones à faible et fort défi sécuritaire "
        "(fort : au moins 5 événements violents pour 100 000 habitants sur 12 mois, ACLED).")
d.add_heading("Résultats par modèle", 2)
tableau(d, ["Modèle", "Erreur moyenne (pts)", "RMSE (pts)", "Corrélation de rang", "Part des abandons dans le top 10 % prévu", "Rappel du top 10 %"],
        [[NOM[m.modele], f"{m.mae:.2f}", f"{m.rmse:.2f}", f"{m.spearman:.2f}", f"{m.part_abandons_captee_top10pct*100:.1f} %", f"{m.rappel_top10pct*100:.0f} %"]
         for m in sy.itertuples()], [4.5, 2.4, 2, 2.4, 3.3, 2.4], taille=7.5)
image(d, tmp / "mae.png", 15, "Figure 1. Erreur absolue moyenne par année prévue.")
para(d, "Lecture : les années 2015 et 2016 sont calmes (erreur de 1 à 2 points). À partir de 2017, l'insécurité et les fermetures d'écoles "
        "font monter l'erreur de tous les modèles ; le gradient boosting reste le meilleur ou à égalité sauf en 2023, année de réouvertures où la "
        "reconduction fait mieux.")
d.add_heading("Calibration, intervalles et équité", 2)
image(d, tmp / "calib.png", 16, "Figure 2. À gauche, prévu contre observé par décile de prévision ; à droite, part des valeurs observées dans l'intervalle à 80 %.")
para(d, f"Couverture moyenne des intervalles : {B['couverture_80_moyenne']*100:.0f} % pour une cible de 80 %. Demi-largeur actuelle : "
        f"± {fr(B['intervalle_80_demi_largeur_points_par_zone']['faible'])} points (défi faible), ± {fr(B['intervalle_80_demi_largeur_points_par_zone']['fort'])} "
        "points (défi fort). Le modèle sous-estime les déciles les plus élevés : les pics d'abandon liés aux fermetures restent au-dessus de la prévision.")
tableau(d, ["Groupe", "Erreur moyenne (pts)", "Biais moyen (pts)", "Observations"],
        [[g.groupe, f"{g.mae:.2f}", f"{g.biais_moyen:+.2f}", int(g.n)] for g in eq.itertuples()], [7, 3, 3, 3], taille=7.5)
para(d, "Équité : un biais négatif signifie que le modèle prévoit moins d'abandon qu'observé, donc qu'il risque d'oublier ce groupe. Ces "
        "écarts sont à garder en tête pour la lecture des cartes.")
d.add_heading("Test rétrospectif : l'année de crise 2021-22", 2)
para(d, f"Avec les seules données disponibles à la rentrée 2022, le modèle prévoyait {r['abandon_national_prevu_modele']:.1f} % d'abandon au niveau "
        f"national (reconduction : {r['abandon_national_prevu_reconduction']:.1f} %) ; l'annuaire a ensuite publié {r['abandon_national_observe']:.1f} %. "
        "L'écart vient pour l'essentiel des fermetures d'écoles : corrigé de leur effet, l'abandon 2021-22 est d'environ 8,6 %. "
        f"Parmi les 5 provinces au plus fort abandon observé ({', '.join(r['provinces_top10_observees'])}), le modèle en avait placé "
        f"{int(r['rappel_modele']*5)} dans ses 5 premières ({', '.join(r['provinces_top10_prevues_modele'])}), la reconduction aucune.")
d.add_heading("Post-primaire", 2)
para(d, f"Les taux publiés par province ne couvrent que 2017-18 à 2023-24, sans 2022-23 : trop peu d'années pour entraîner un modèle. "
        f"La reconduction y fait une erreur moyenne de {B['post_primaire_mae_reconduction_points']:.1f} points. Le post-primaire est donc présenté en "
        "mesure (fiches, application), pas en prévision.")
d.add_heading("Ce que la prévision permet, et ne permet pas", 2)
puces(d, ["Elle permet de classer les provinces et de préparer les moyens dès la rentrée, avant la publication de l'annuaire.",
          "Elle ne remplace pas la mesure : la valeur exacte d'une province en zone d'insécurité peut s'écarter fortement de la prévision.",
          "Les contributions des facteurs (SHAP) indiquent des associations dans le modèle, pas des causes prouvées."])
p = ROOT / "livrables" / "04_analyse" / f"{TEAM}_04-analyse_D1_scientist_rapport-fiabilite_v1.docx"
if enregistrer(d, p): p.unlink()
for f in tmp.glob("*"): f.unlink()
tmp.rmdir()
print("ok")
