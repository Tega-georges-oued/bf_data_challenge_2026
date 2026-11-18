"""T16 / L08 - LISEZ-MOI des dépôts 02 à 05 et LISEZ-MOI général, générés à partir du contenu réel des dossiers.

Usage : python t16_lisez_moi.py [--racine CHEMIN_BF_DATA_CHALLENGE]
Le LISEZ-MOI de 01_collecte, rédigé à la main, n'est pas remplacé.
"""
import argparse, datetime
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[3])
ROOT = ap.parse_args().racine
TEAM = "VIGIE-Ecole-Team"
AUJ = datetime.date.today().isoformat()

DESC = {
 # 02
 "effectifs-primaire-provinces-consolide": "Effectifs et redoublants du primaire par ancienne province (45), année (2008-09 à 2024-25), classe et sexe. Série de référence.",
 "effectifs-primaire-provinces_": "Effectifs lus dans les tableaux historiques (VIII.3) des annuaires, avant consolidation.",
 "toutes-editions": "Toutes les lectures des tableaux historiques, édition par édition (traçabilité des corrections).",
 "ressources-primaire-provinces": "Écoles, maîtres chargés de cours et salles de classe par ancienne province et année (tableau I.1).",
 "journal": "Journal de nettoyage : problème rencontré, correction, lignes touchées.",
 "controle": "Contrôle : comparaison de nos totaux avec les publications ou la base principale du challenge.",
 # 03
 "flux-primaire-45": "Flux de cohorte par ancienne province : élèves, sorties nettes, abandon par classe, écoles, effet des fermetures.",
 "indicateurs-decrochage-47-provinces": "Abandon publié (DGESS), sortie nette, effet des fermetures, abandon corrigé, post-primaire, secondaire : 47 provinces, par sexe.",
 "indicateurs-decrochage-17-regions": "Mêmes indicateurs agrégés sur les 17 régions.",
 "indicateurs-decrochage-national": "Mêmes indicateurs au niveau national.",
 "table-analyse-47-provinces": "Table d'analyse : une ligne par province et année, avec l'abandon, ses valeurs passées et tous les facteurs (ressources, ACLED, CONASUR, RGPH 2019, distance). Les lignes ligne_prevision=True sont à prévoir.",
 "dictionnaire-variables": "Dictionnaire : définition, unité, source et calcul de chaque variable des dépôts 03 et 04.",
 "schema-donnees": "Schéma des données : tables, clés et relations ; règles d'intégrité vérifiées.",
 "parcours-donnees": "Plan du parcours des données, des sources à l'application ; règle de disponibilité de l'information.",
 # 04
 "previsions-hors-echantillon": "Prévisions faites pour chaque année 2015-2023 avec les seules années antérieures (validation).",
 "fiabilite-par-annee-test": "Erreurs des trois modèles par année prévue.",
 "fiabilite-synthese-modeles": "Erreurs moyennes, corrélation de rang et capacité à repérer le top 10 %, par modèle.",
 "couverture-intervalles-80": "Couverture et largeur des intervalles à 80 % par année et zone de sécurité.",
 "calibration-deciles": "Prévu contre observé par décile de prévision.",
 "equite-erreurs-par-groupe": "Erreurs et biais par groupe (filles, garçons, zones de sécurité, grandes villes).",
 "prevision-abandon-primaire-2024-25-47-provinces": "PRÉVISION 2024-25 par province : valeur, intervalle à 80 %, niveau d'alerte, élèves à risque, cause dominante, trois facteurs principaux.",
 "explication-facteurs-shap": "Contribution de chaque facteur à la prévision de chaque province (SHAP), avec sa famille.",
 "importance-globale-facteurs": "Importance moyenne de chaque facteur sur l'ensemble des prévisions.",
 "typologie-17-regions": "Profil des 17 régions selon les familles de facteurs, et groupe.",
 "bilan-modele": "Bilan chiffré du modèle (JSON) : erreurs, seuils d'alerte, test rétrospectif 2021-22.",
 "rapport-fiabilite": "Rapport de fiabilité : protocole, erreurs par année, calibration, équité, test 2021-22, limites.",
 # 05
 "fiche-region-": "Fiche d'une page pour une région.",
 "fiches-17-regions": "Les 17 fiches régionales réunies, de la région la plus exposée à la moins exposée.",
 "atlas-national": "Atlas national en 8 pages : alerte, abandon corrigé, fermetures, filles, insécurité, profils, facteurs, classement.",
 "prevision-abandon-primaire-2024-25-17-regions": "Prévision 2024-25 agrégée par région (moyenne pondérée par les élèves), rang et profil.",
 "documentation": "Documentation du projet (plan en 7 parties de la commission), en Word et en PDF.",
}
ETAPES = {
 "02_nettoyage": ("Données propres et journal de nettoyage", "engineer",
   "Les annuaires du primaire (MEBAPLN-DGESS) sont lus en PDF. Les tableaux historiques donnent 2008-09 à 2016-17 ; les tableaux détaillés de chaque "
   "annuaire donnent 2017-18 à 2024-25, car la répartition par sexe des tableaux historiques est fausse pour 2024-25. Contrôle : 387 cases "
   "région-année-sexe sur 390 identiques à la base principale du challenge. Scripts : livrables/app/pipeline/t04_primaire.py, t04b_consolider_primaire.py."),
 "03_transformation": ("Base harmonisée, schéma, dictionnaire, plan du parcours", "architect",
   "Abandon calculé par la cohorte reconstituée (méthode ISU/DGESS, CP1 à CM1), vérifié contre le tableau I.8 des annuaires ; abandon corrigé des "
   "fermetures et réouvertures d'écoles ; passage des 45 anciennes aux 47 nouvelles provinces par les communes. "
   "Scripts : livrables/app/pipeline/t07_indicateurs.py, t08_facteurs.py, t15a_dictionnaire.py, t15b_schema_parcours_fiabilite.py."),
 "04_analyse": ("Modèle, fiabilité, prévisions, facteurs, typologie", "scientist et analyst",
   "Gradient boosting comparé à la reconduction et à une régression ridge ; validation temporelle 2015-2023 ; intervalles à 80 % par zone de sécurité ; "
   "explication SHAP ; typologie des régions. Toutes les variables sont celles connues à la rentrée. Script : livrables/app/pipeline/t09_modele.py."),
 "05_interpretation": ("Fiches, atlas, documentation", "analyst",
   "L'application est dans le dossier livrables/app (lancement : streamlit run livrables/app/app.py). Les fiches et l'atlas sont produits par livrables/app/pipeline/t14_fiches_atlas.py, "
   "la documentation par t15c_documentation.py. Les pistes d'action sont des propositions à valider par l'équipe éducative."),
}

def decrire(nom):
    for k, v in DESC.items():
        if k in nom:
            if k == "fiche-region-":
                return v.replace("une région", "la région " + nom.split("fiche-region-")[1].split("_v")[0].replace("-", " ").title())
            return v
    return ""

for dossier, (titre, role, texte) in ETAPES.items():
    d = ROOT / "livrables" / dossier
    fichiers = sorted(f for f in d.glob("*") if f.is_file() and "LISEZ-MOI" not in f.name)
    L = [f"{TEAM} · Dépôt {dossier} · {titre}", "=" * 70, f"Rôle : {role} · Défi 1 (décrochage scolaire) · mis à jour le {AUJ}", "",
         texte, "", "Découpage : 17 régions et 47 provinces (2025). Séparateur des CSV : point-virgule ; encodage UTF-8 ; décimales avec un point.",
         "Nommage : VIGIE-Ecole-Team_ETAPE_D1_ROLE_description_vN.", "", f"Fichiers ({len(fichiers)}) :", ""]
    if dossier == "05_interpretation":
        L[6:6] = ["Ordre de lecture conseillé : rapport final pour la méthode, atlas national pour comparer les régions, puis fiches régionales pour examiner les alertes par province.", ""]
    for f in fichiers:
        L += [f"- {f.name}", f"    {decrire(f.name)}"]
    L += ["", "Sources : annuaires MEBAPLN-DGESS et MESFPT-DGESS ; INSD (RGPH 2019) ; ACLED ; CONASUR ; IGB/OCHA COD-AB. Détail : 01_collecte, registre des sources."]
    (d / f"{TEAM}_{dossier.replace('_', '-', 1)}_D1_{role.split()[0]}_LISEZ-MOI_v1.txt").write_text("\n".join(L), encoding="utf-8")

G = [f"{TEAM} · VIGIE-École · LISEZ-MOI général", "=" * 70, f"Data Challenge Burkina 2026, Édition Éducation · Défi 1 · mis à jour le {AUJ}", "",
     "VIGIE-École mesure l'abandon scolaire réel au primaire (corrigé des fermetures d'écoles), le prévoit dès la rentrée pour les 47 provinces,",
     "explique ce qui pèse dans le risque et aide à décider où agir, sur le découpage de 2025 en 17 régions.", "",
     "Par où commencer", "---------------",
     "1. Rapport final — comprendre le problème, les données, la méthode, les résultats et leurs limites.",
     "2. Atlas national (8 pages) — voir où le risque se concentre et comparer les 17 régions.",
     "3. Fiches des 17 régions — choisir une région et examiner ses alertes province par province.",
     "4. Application — explorer les cartes et les fiches de façon interactive.",
     "",
     "Les trois PDF sont dans livrables/05_interpretation.",
     "Pour lancer l'application localement depuis la racine du projet :",
     "  pip install -r livrables/app/requirements.txt",
     "  streamlit run livrables/app/app.py", "",
     "Les cinq dépôts", "---------------"]
for dossier in ["01_collecte", "02_nettoyage", "03_transformation", "04_analyse", "05_interpretation"]:
    n = len([f for f in (ROOT / "livrables" / dossier).glob("*") if f.is_file()])
    G.append(f"- {dossier:18} {n:3} fichiers · {ETAPES.get(dossier, ('Données brutes référencées, registre des sources, référentiel géographique',))[0]}")
G += ["", "Versions", "--------", "- v1 : tous les fichiers, sauf la série du primaire consolidée (02_nettoyage, v2 : années 2017-18 à 2024-25 reprises des tableaux détaillés).", "",
      "Relancer tout le travail", "------------------------", "python livrables/app/relancer.py            (toutes les étapes, puis contrôle des sorties)",
      "python livrables/app/relancer.py --depuis t09   (à partir d'une étape)", "",
      "Autres dossiers", "---------------", "- donnees : sources brutes (annuaires, RGPH, ACLED, CONASUR, limites) ; - livrables/app : application et scripts (livrables/app/pipeline) ;",
      "- pilotage : plan de travail et journal."]
for p in [ROOT / "LISEZ-MOI.txt", ROOT / "livrables" / "05_interpretation" / f"{TEAM}_05-interpretation_D1_analyst_LISEZ-MOI-general_v1.txt"]:
    p.write_text("\n".join(G), encoding="utf-8")
print("LISEZ-MOI écrits")
