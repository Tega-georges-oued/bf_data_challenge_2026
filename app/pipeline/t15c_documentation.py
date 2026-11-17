"""T15 - Documentation (15 pages au plus, plan en 7 parties conseillé par la commission). Dépôt 05_interpretation.

Usage : python t15c_documentation.py [--racine CHEMIN_BF_DATA_CHALLENGE]
Sorties : 05_interpretation/VIGIE-Ecole-Team_05-interpretation_D1_analyst_documentation_v1.docx et .pdf
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_outils import nouveau, para, puces, tableau, image, enregistrer
from docx.shared import Pt

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[2])
ROOT = ap.parse_args().racine
DIAG = Path(__file__).resolve().parent / "diagrammes"
TEAM = "VIGIE-Ecole-Team"
def latest(folder, pat):
    return sorted((ROOT / folder).glob(f"*{pat}*"))[-1]
def f1(x, d=1):
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

prev = pd.read_csv(latest("04_analyse", "prevision-abandon-primaire-2024-25-47"), sep=";")
reg = pd.read_csv(latest("05_interpretation", "prevision-abandon-primaire-2024-25-17-regions"), sep=";")
imp = pd.read_csv(latest("04_analyse", "importance-globale-facteurs"), sep=";")
nat = pd.read_csv(latest("03_transformation", "indicateurs-decrochage-national"), sep=";")
B = json.load(open(latest("04_analyse", "bilan-modele"), encoding="utf-8"))
geo2 = json.load(open(ROOT / "app/data/limites_admin2_simplifiees.geojson", encoding="utf-8"))
geo1 = json.load(open(ROOT / "app/data/limites_admin1_simplifiees.geojson", encoding="utf-8"))
nT = nat[nat.sexe == "T"].set_index("annee_depart")
em = B["erreur_mediane_points_par_zone_gbm"]
nat_prev = np.average(prev.prevision, weights=prev.effectif_cp1_cm1_2024)
tmp = ROOT / "05_interpretation" / "_fig"; tmp.mkdir(exist_ok=True)

# figures
fig, ax = plt.subplots(figsize=(7.2, 3.1))
x = nT.index.str[:4].astype(int) + 1
ax.bar(x, nT.taux_effet_fermetures, color="#bdc3c7", label="Effet des fermetures (+) / réouvertures (−)")
ax.plot(x, nT.taux_abandon_dgess, "-o", ms=3, color="#c0392b", label="Abandon publié (convention DGESS)")
ax.plot(x, nT.taux_abandon_corrige, "-o", ms=3, color="#2c3e50", label="Abandon corrigé (VIGIE-École)")
ax.axhline(0, color="black", lw=.5); ax.set_ylabel("% des élèves CP1-CM1"); ax.set_xlabel("Année scolaire (année de fin)")
ax.legend(frameon=False, fontsize=7.5); ax.grid(alpha=.3); ax.spines[["top", "right"]].set_visible(False)
fig.savefig(tmp / "national.png", dpi=180, bbox_inches="tight"); plt.close(fig)

def polys(ft):
    g = ft["geometry"]; return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
AL = {"rouge": "#c0392b", "orange": "#e67e22", "jaune": "#f1c40f"}
na = prev.set_index("adm2_pcode").niveau_alerte
fig, ax = plt.subplots(figsize=(6, 4.6))
for ft in geo2["features"]:
    for p in polys(ft):
        ax.add_patch(MPoly(np.array(p[0]), fc=AL.get(na.get(ft["properties"]["adm2_pcode"]), "#ddd"), ec="white", lw=.4))
for ft in geo1["features"]:
    for p in polys(ft):
        ax.add_patch(MPoly(np.array(p[0]), fc="none", ec="#333", lw=.9))
    a = np.array(max(polys(ft), key=lambda q: len(q[0]))[0])
    ax.text(a[:, 0].mean(), a[:, 1].mean(), ft["properties"]["adm1_name"], fontsize=6.5, ha="center", bbox=dict(fc="white", alpha=.6, lw=0, pad=.4))
ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
ax.legend(handles=[Patch(fc=v, label=k.capitalize()) for k, v in AL.items()], loc="lower right", frameon=False)
fig.savefig(tmp / "carte.png", dpi=180, bbox_inches="tight"); plt.close(fig)

# ======================================================================
d = nouveau("VIGIE-École : voir venir le décrochage scolaire et décider où agir",
            "Data Challenge Burkina 2026 · Édition Éducation · Défi 1 : cartographie et anticipation du risque de décrochage scolaire par région · "
            "Équipe VIGIE-Ecole-Team")
para(d, "En une phrase. ", None)
d.paragraphs[-1].runs[0].bold = True
d.paragraphs[-1].add_run(f"VIGIE-École mesure l'abandon réel au primaire en séparant les élèves qui quittent l'école de ceux que la fermeture "
                         f"d'écoles a fait sortir, prévoit dès la rentrée le risque d'abandon de chacune des 47 provinces ({f1(nat_prev)} % au niveau "
                         f"national pour 2024-25, soit environ {f1(prev.decrocheurs_attendus.sum(), 0)} élèves), explique ce qui pèse dans ce risque, et "
                         "propose où et comment agir, sur le découpage de 2025 en 17 régions.")

# ---------- 1 ----------
d.add_heading("1. Le défi", 1)
para(d, "Notre question, dans nos mots : à la rentrée, avant que l'annuaire ne publie les chiffres de l'année écoulée, où des élèves sont-ils en "
        "train de quitter l'école, pourquoi, et où mettre les moyens en premier ?")
para(d, "Trois constats ont orienté notre réponse. D'abord, le taux d'abandon publié arrive tard : l'abandon de l'année t n'est connu qu'avec "
        "l'annuaire t+1, publié en cours d'année t+2. Ensuite, depuis 2018, ce taux mélange deux réalités que le décideur traite différemment : "
        "les élèves qui abandonnent, et ceux que la fermeture de leur école a fait sortir des statistiques, puis qui reviennent quand elle rouvre. "
        "Enfin, une carte du risque ne suffit pas : le directeur régional a besoin de savoir quel type de réponse convient à chaque province.")
para(d, "VIGIE-École répond donc à trois questions, dans cet ordre :")
puces(d, [("Mesurer : ", "quel est l'abandon réel, corrigé des fermetures et réouvertures d'écoles, par province, région, niveau et sexe ?"),
          ("Anticiper : ", "quel sera l'abandon de l'année en cours, province par province, avec quelle marge d'erreur ?"),
          ("Décider : ", "quels facteurs pèsent dans chaque province, quel type d'action en découle, et où une action donnée touche-t-elle le plus d'élèves à risque ?")])
para(d, "L'équipe réunit un étudiant ingénieur en intelligence artificielle et science des données (collecte, préparation, modèle, application) "
        "et un conseiller d'éducation (lecture terrain des résultats, grille d'actions, fiches régionales). Le travail porte sur les 17 régions "
        "et 47 provinces du découpage de 2025.")

# ---------- 2 ----------
d.add_heading("2. Les données", 1)
para(d, "Toutes les données sont publiques. Le registre des sources (dépôt 01_collecte) recense 248 fichiers avec leur producteur, leur "
        "publication, leur année, leur date d'extraction et une empreinte MD5.")
tableau(d, ["Source (producteur)", "Ce que nous en tirons", "Années", "Limites"], [
    ["Annuaires statistiques de l'éducation préscolaire, primaire et non formelle (MEBAPLN, DGESS)",
     "Effectifs et redoublants par province, niveau et sexe ; écoles, maîtres, salles ; distances domicile-école ; taux publiés (contrôle)",
     "2008-09 à 2024-25", "Publiés sur les 45 anciennes provinces ; nombre d'écoles par province seulement depuis 2017-18 ; erreurs de libellés dans les tableaux historiques"],
    ["Annuaires statistiques du post-primaire et du secondaire (MESFPT, DGESS)", "Taux d'abandon publiés par province et classe (tableau II.3.11)",
     "2017-18 à 2023-24", "2022-23 absent ; trop court pour un modèle"],
    ["Recensement général de la population 2019 (INSD) et cartographie de la pauvreté (INSD, EHCVM 2018)",
     "Population des 351 communes ; enfants hors de l'école, travail des enfants, mariage des filles, alphabétisation, électricité, pauvreté",
     "2019", "Photographie fixe ; antérieure aux grands déplacements de population"],
    ["ACLED (via HDX)", "Événements violents, violences contre les civils et décès, par province et par mois", "2015 à sept. 2025",
     "Fondé sur les médias et rapports ; sous-déclaration possible dans les zones isolées"],
    ["CONASUR (via HDX)", "Personnes déplacées internes par commune", "Relevés 2019 à 2025", "Communes non toutes renseignées à chaque relevé (couverture indiquée)"],
    ["IGB / OCHA, COD-AB", "Limites et codes des 17 régions, 47 provinces, 351 communes ; correspondance avec les anciens codes", "2025", "—"],
], [4.3, 5.3, 2.2, 5.2], taille=7.3)
para(d, "Pourquoi pas plus fin que la province ? Les annuaires publics ne donnent pas les effectifs par commune ou par école sur la durée. "
        "Pourquoi le primaire d'abord ? C'est le seul niveau pour lequel on dispose de 17 années de données comparables, ce qu'exige un modèle "
        "de prévision ; le post-primaire est mesuré et cartographié, mais pas prévu.")
para(d, "Le piège du découpage. ", None); d.paragraphs[-1].runs[0].bold = True
d.paragraphs[-1].add_run("Les annuaires utilisent les 13 anciennes régions et 45 provinces ; le défi porte sur les 17 nouvelles régions. Les deux "
                         "ne se recoupent pas : deux anciennes provinces (Soum et Tapoa) ont été coupées en deux. Nous passons par les communes, "
                         "dont chacune connaît son ancienne et sa nouvelle province.")

# ---------- 3 ----------
d.add_heading("3. La préparation", 1)
d.add_heading("Nettoyage : ce que nous avons corrigé et pourquoi", 2)
tableau(d, ["Problème rencontré", "Correction", "Contrôle"], [
    ["Tableaux historiques des annuaires (PDF) : années mal étiquetées, blocs en double, une année manquante (Mouhoun, Kourittenga, Ganzourgou, Boulkiemdé, Sanguié)",
     "Lecture des PDF en mise en page fixe ; chaque année validée si ses totaux se retrouvent dans un autre annuaire ; doublons retirés", "Totaux nationaux comparés aux publications"],
    ["Répartition filles / garçons fausse dans le tableau historique de 2024-25", "Années 2017-18 à 2024-25 reprises des tableaux détaillés de chaque annuaire",
     "387 cases région-année-sexe sur 390 identiques à la base principale du challenge (écart maximal : 41 élèves)"],
    ["Filles + garçons ≠ total (Oubritenga 2010-11)", "Signalé, non modifié (7 cases)", "Journal de nettoyage"],
    ["Komandjari 2022-23 : aucun élève, nombre d'écoles manquant", "Écoles fixées à 0 (écoles toutes fermées)", "Cohérent avec les effectifs"],
    ["Noms de communes écrits de plusieurs façons (RGPH, COD-AB)", "Rapprochement approché (46 cas) revu un par un ; table d'alias", "351 communes ; population totale 20 505 155, égale au chiffre officiel"],
    ["Arrondissements de Ouagadougou et Bobo-Dioulasso", "Sommés pour former les communes", "—"],
], [6, 6, 5], taille=7.3)
d.add_heading("Transformation : les variables créées", 2)
para(d, "L'abandon est calculé par la méthode de la cohorte reconstituée (UNESCO-ISU), celle de la DGESS : pour chaque classe g de CP1 à CM1, "
        "les élèves de l'année t qui ne sont ni promus ni redoublants en t+1 sont sortis :")
para(d, "sorties(g) = effectif(g, t) − [effectif(g+1, t+1) − redoublants(g+1, t+1)] − redoublants(g, t+1)", italique=True)
para(d, "Le CM2 est exclu (sortie par l'examen). En ramenant à zéro les valeurs négatives, comme la DGESS, nous retrouvons exactement les taux "
        "publiés par l'annuaire (tableau I.8) : c'est notre taux « publié ». Nous ajoutons deux mesures :")
puces(d, [("Effet des fermetures : ", "élèves × variation relative du nombre d'écoles de la province entre t et t+1. Positif quand des écoles ferment, "
           "négatif quand elles rouvrent et que des élèves reviennent."),
          ("Abandon corrigé : ", "(sorties nettes − effet des fermetures) / élèves, borné à zéro. Il approche les élèves qui ont réellement "
           "quitté l'école. Quand le nombre d'écoles varie de plus de 10 %, la correction est fragile et signalée comme telle.")])
para(d, "Les flux sont calculés sur les 45 anciennes provinces puis reportés sur les 47 provinces avec la population 2019 des communes "
        "(Soum : 65,58 % Djelgodji, 34,42 % Karo-Peli ; Tapoa : 31,47 % Dyamongou, 68,53 % Gobnangou). Les ratios d'encadrement (élèves par maître, "
        "par salle), le redoublement, la part des filles, la distance, les indicateurs du RGPH, l'insécurité (ACLED) et les déplacements (CONASUR) "
        "sont joints dans une table d'analyse de 47 provinces × 17 années. Le dictionnaire des variables (dépôt 03) donne pour chacune sa "
        "définition, son unité, sa source et son calcul.")

# ---------- 4 ----------
d.add_heading("4. La méthode", 1)
d.add_heading("Une règle : n'utiliser que ce qui est connu à la rentrée", 2)
para(d, "La prévision de l'abandon de l'année t est faite en octobre de l'année t+1, avant la publication de l'annuaire. Elle n'utilise que : "
        "l'abandon de l'année précédente (t−1), les ressources de l'année t (écoles, maîtres, salles, distances), les violences d'octobre t à "
        "septembre t+1 et celles des trois mois précédant la rentrée, le dernier relevé des personnes déplacées et le contexte du RGPH 2019. "
        "Cette règle évite qu'un modèle paraisse précis grâce à des informations qu'un décideur n'aurait pas eues.")
d.add_heading("Trois modèles comparés, le plus simple comme référence", 2)
puces(d, [("Reconduction : ", "l'abandon de l'an dernier est reconduit. C'est ce que fait un décideur sans modèle ; tout modèle doit faire mieux."),
          ("Régression ridge : ", "relation linéaire entre les facteurs et l'abandon, avec pénalisation pour éviter le sur-apprentissage."),
          ("Gradient boosting (HistGradientBoosting) : ", "arbres de décision peu profonds combinés ; capte les seuils et les interactions "
           "(par exemple, l'effet de l'insécurité qui dépend de l'offre scolaire) et tolère les données manquantes.")])
para(d, f"Validation temporelle : chaque année de 2015 à 2023 est prévue avec les seules années antérieures, comme en conditions réelles "
        f"({B['n_lignes_apprentissage']} lignes province-année). Le gradient boosting est retenu : il réduit l'erreur de "
        f"{B['gain_mae_vs_reconduction_pct']} % par rapport à la reconduction et classe mieux les provinces (corrélation de rang "
        f"{B['spearman_par_modele']['gbm']} contre {B['spearman_par_modele']['reconduction']}).")
d.add_heading("Une marge d'erreur honnête", 2)
para(d, "Chaque prévision porte un intervalle à 80 %, construit à partir des erreurs réellement commises les trois années précédentes "
        "(méthode conforme), séparément pour les provinces à faible et à fort défi sécuritaire. Le seuil retenu pour « fort » est de 5 événements "
        "violents pour 100 000 habitants sur 12 mois.")
d.add_heading("Expliquer, regrouper, cibler", 2)
puces(d, [("Explication : ", "les valeurs de Shapley (SHAP) donnent, pour chaque province, la contribution de chaque facteur à sa prévision. Nous les "
           "regroupons en cinq familles : inertie scolaire, insécurité et déplacements, offre scolaire et distance, pauvreté et travail des enfants, "
           "situation des filles. La famille à la contribution positive la plus forte donne la « cause dominante »."),
          ("Typologie : ", "les 17 régions sont regroupées (k-moyennes, 4 groupes) selon le profil de ces familles, ce qui oriente le type de réponse."),
          ("Ciblage : ", "une grille relie chaque famille de facteurs à des actions à trois niveaux (établissement, CEB ou province, région). Le "
           "simulateur alloue une action aux provinces au risque prévu le plus élevé et calcule les abandons évités selon une efficacité que "
           "l'utilisateur renseigne lui-même : les données ne permettent pas de la mesurer.")])
para(d, "Pourquoi pas un modèle plus complexe ? Avec 47 provinces et 17 années, un réseau de neurones apprendrait le bruit. Un gradient boosting "
        "peu profond, comparé à une référence simple et expliqué province par province, est à la fois plus fiable et plus lisible pour un décideur.")

# ---------- 5 ----------
d.add_heading("5. Les résultats", 1)
d.add_heading("Un abandon réel sous-estimé depuis la réouverture des écoles", 2)
image(d, tmp / "national.png", 15.5, "Figure 1. Abandon au primaire (CP1-CM1), Burkina Faso. Sources : annuaires DGESS ; calcul VIGIE-École.")
a21, a22, a23 = nT.loc["2021/2022"], nT.loc["2022/2023"], nT.loc["2023/2024"]
para(d, f"En 2021-22, l'abandon publié atteint {f1(a21.taux_abandon_dgess)} % ; {f1(a21.taux_effet_fermetures)} points viennent des fermetures "
        f"d'écoles, et l'abandon corrigé est de {f1(a21.taux_abandon_corrige)} %. À l'inverse, en 2022-23 et 2023-24, les réouvertures font "
        f"revenir des élèves qui compensent, dans le taux publié, des abandons réels : l'abandon publié est de {f1(a22.taux_abandon_dgess)} % "
        f"puis {f1(a23.taux_abandon_dgess)} %, l'abandon corrigé de {f1(a22.taux_abandon_corrige)} % puis {f1(a23.taux_abandon_corrige)} %. "
        "Lire le seul taux publié conduirait à conclure que la crise est passée ; la mesure corrigée dit le contraire.")
d.add_heading("Où le risque est le plus élevé en 2024-25", 2)
image(d, tmp / "carte.png", 11.5, "Figure 2. Niveau d'alerte par province. Rouge : 20 % des provinces au risque prévu le plus élevé.")
top = prev.sort_values("prevision", ascending=False).head(8)
para(d, f"Abandon prévu au niveau national : {f1(nat_prev)} %. Provinces les plus exposées : " +
        ", ".join(f"{r.adm2_name} ({f1(r.prevision)} %)" for r in top.itertuples()) + ". Le risque est concentré au nord et à l'est, mais "
        "des provinces du sud-ouest (Poni) et du centre-est (Boulgou) apparaissent aussi en rouge.")
tableau(d, ["Rang", "Région", "Abandon prévu", "Élèves à risque", "Provinces rouges", "Profil des facteurs"],
        [[int(r.rang), r.adm1_name, f1(r.prevision) + " %", f1(r.decrocheurs_attendus, 0), f"{int(r.provinces_alerte_rouge)} / {int(r.provinces)}",
          r.profil_regional.replace("Dominante : ", "")] for r in reg.itertuples()], [1.1, 2.3, 2.2, 2.3, 2.3, 6.8], taille=7)
d.add_heading("Ce qui pèse dans le risque", 2)
fam = imp.groupby("famille").shap_moyen_absolu_points.sum().sort_values(ascending=False)
para(d, "Par ordre de poids dans la prévision : " + " ; ".join(f"{k.lower()} ({f1(v)} pt)" for k, v in fam.items()) + ". Les facteurs individuels "
        "les plus influents sont : " + " ; ".join(imp.head(5).libelle) + ". Quatre profils régionaux en découlent : le Liptako, la Sirba et le "
        "Soum, où pauvreté, travail des enfants et situation des filles dominent ; le Djôrô, le Koulsé, le Nakambé et le Yaadga, où l'insécurité "
        "s'ajoute à une offre scolaire tendue ; la Tapoa, marquée par l'inertie et la pauvreté ; les autres régions, où l'offre scolaire et la "
        "distance sont le premier levier.")
d.add_heading("Fiabilité", 2)
para(d, f"Erreur typique de la prévision : {f1(em['faible'])} points dans les zones à faible défi sécuritaire, {f1(em['fort'])} points dans les zones à fort "
        f"défi sécuritaire, où une fermeture massive d'écoles peut faire sortir la majorité des élèves en un an. Le modèle retrouve "
        f"{B['rappel_top10pct']['gbm']*100:.0f} % des provinces du top 10 % (reconduction : {B['rappel_top10pct']['reconduction']*100:.0f} %). "
        "Testé sur l'année de crise 2021-22 avec les seules données de la rentrée 2022, il plaçait 2 des 5 provinces les plus touchées parmi ses "
        "5 premières, la reconduction aucune. Il ne prévoyait pas l'ampleur du pic national, dû aux fermetures. Le rapport de fiabilité (dépôt 04) "
        "détaille les erreurs par année, la calibration et l'équité entre filles et garçons.")
d.add_heading("La solution : application, fiches, atlas", 2)
image(d, DIAG / "app_carte.png", 15.5, "Figure 3. Application VIGIE-École, page « Carte d'alerte ».")
puces(d, [("Application VIGIE-École (hors connexion) : ", "carte d'alerte, fiche par région et par province (évolution par sexe, facteurs), "
           "« Comprendre l'abandon » (publié contre corrigé), simulateur de ciblage, fiabilité, perspective."),
          ("17 fiches régionales d'une page : ", "chiffres clés, carte des provinces, évolution 2009-2024 (publié, filles, corrigé, post-primaire), "
           "tableau des provinces avec fourchette et facteurs, pistes d'action."),
          ("Atlas national (8 pages) : ", "alerte, abandon corrigé, effet des fermetures en 2021-22, écart filles-garçons, pression sécuritaire, "
           "profils régionaux, familles de facteurs, classement des régions.")])
image(d, DIAG / "app_province.png", 12.5, "Figure 4. Fiche province : contribution des facteurs à la prévision.")

# ---------- 6 ----------
d.add_heading("6. La réponse au défi", 1)
d.add_heading("Comment un décideur s'en sert", 2)
puces(d, [("En octobre, à la rentrée : ", "la direction régionale ouvre la carte d'alerte, repère ses provinces rouges et orange et la cause dominante "
           "de chacune ; elle n'attend plus l'annuaire, publié plus d'un an plus tard."),
          ("En novembre, pour répartir les moyens : ", "avec le simulateur, elle compare où une action (cantines, enseignants, accueil des déplacés, "
           "bourses pour les filles) touche le plus d'élèves à risque, et en discute avec les CEB à partir des fiches d'une page."),
          ("Chaque mois : ", "les nouvelles données de sécurité et de déplacements mettent à jour le signal de l'année en cours."),
          ("À la publication de l'annuaire : ", "la mesure corrigée vérifie la prévision et dit si l'abandon a réellement baissé, au-delà de l'effet des réouvertures.")])
d.add_heading("Limites", 2)
puces(d, ["La province est l'échelle la plus fine permise par les données publiques ; les écoles et les élèves à risque ne sont pas identifiés.",
          "Dans les zones à fort défi sécuritaire, la valeur prévue d'une province peut s'écarter fortement de la réalité ; la carte y sert à classer.",
          "La correction des fermetures suppose qu'une école fermée retire une part moyenne des élèves de la province ; elle est fragile quand le "
          "nombre d'écoles varie de plus de 10 %.",
          "Les facteurs expliquent la prévision, ils ne prouvent pas une cause. La grille d'actions est une proposition à valider par les acteurs de "
          "terrain, et l'efficacité des actions reste une hypothèse.",
          "Le post-primaire n'est pas prévu, faute d'années de données suffisantes."])
d.add_heading("La suite : de VIGIE-École à FASO SCHOOL TRACKER", 2)
para(d, "Collecter à nouveau les données partout, chaque année, est coûteux et lent. La suite logique est un système de suivi scolaire national, "
        "de la maternelle à l'université, que notre équipe porte depuis plusieurs années sous le nom de FASO SCHOOL TRACKER. VIGIE-École est "
        "conçu pour en recevoir les données sans être refait :")
tableau(d, ["Horizon", "Données", "Alerte", "Délai"], [
    ["Aujourd'hui : VIGIE-École", "Annuaires DGESS, ACLED, CONASUR, RGPH", "Province", "Un an, révisé chaque mois"],
    ["Demain : accès direct à la base de la DGESS", "Recensement scolaire par établissement", "Établissement", "Dès la rentrée"],
    ["Après-demain : FASO SCHOOL TRACKER", "Identifiant unique de l'apprenant, présence, notes, transferts", "Élève", "Au trimestre"],
], [5, 6, 2.5, 3.5], taille=7.5)
para(d, "Seul un identifiant unique de l'apprenant permet de distinguer un abandon d'un transfert ou d'un déplacement. Garde-fous : hébergement "
        "au Burkina Faso, avis de la Commission de l'informatique et des libertés (CIL) et respect de la loi n° 001-2021/AN sur la protection "
        "des données personnelles, aucun score individuel publié, décision toujours laissée à l'équipe éducative. Il s'agit d'une perspective : "
        "aucun résultat n'est simulé ici.")

# ---------- 7 ----------
d.add_heading("7. La reproduction", 1)
para(d, "Outils : Python 3.11 ou plus récent ; bibliothèques listées dans app/requirements.txt (pandas, numpy, scikit-learn, shap, matplotlib, "
        "reportlab, python-docx, streamlit, plotly), testées sous Windows et Linux, Python 3.10 à 3.13. Aucun outil externe n'est obligatoire : le texte des annuaires PDF est livré déjà extrait dans DATAS/Textes_extraits_pdf, avec l'empreinte de chaque PDF ; pdftotext (poppler) ne sert que pour un nouvel annuaire, et LibreOffice seulement pour convertir les rapports Word en PDF.")
tableau(d, ["Étape", "Commande (depuis le dossier BF_DATA_CHALLENGE)", "Produit"], [
    ["Installer", "pip install -r app/requirements.txt", "Environnement"],
    ["Vérifier l'environnement", "python app/relancer.py --verifier", "Versions, fichiers d'entrée, outils facultatifs"],
    ["Tout relancer", "python app/relancer.py", "Contrôle, étapes 1 à 5 dans l'ordre, contrôle des sorties ; journal dans app/relancer_journal.txt"],
    ["Une étape", "python app/relancer.py --depuis t09", "Reprise à partir d'une étape"],
    ["Application", "streamlit run app/app.py", "VIGIE-École dans le navigateur, hors connexion"],
], [2.5, 8.5, 6], taille=7.5)
para(d, "Ordre des scripts (app/pipeline) : t02_referentiel → t03_registre_sources → t04_primaire → t04b_consolider_primaire → t07_indicateurs → "
        "t08_facteurs → t09_modele → t14_fiches_atlas → t15a_dictionnaire → t15b_schema_parcours_fiabilite → t15c_documentation. Chaque "
        "dépôt contient un LISEZ-MOI qui décrit ses fichiers. Le modèle est déterministe : deux exécutions donnent les mêmes prévisions.")
para(d, "Mise à jour avec un nouvel annuaire : déposer le PDF dans DATAS, ajouter l'édition dans t04b_consolider_primaire, puis relancer.")
d.add_heading("Usage de l'intelligence artificielle", 2)
para(d, "Nous avons utilisé deux assistants, Claude (Anthropic) et ChatGPT (OpenAI), sur des données publiques uniquement, aucune donnée "
        "personnelle. Nous leur avons demandé : d'écrire et corriger les scripts d'extraction des tableaux des annuaires PDF, de programmer les "
        "calculs, le modèle, l'application et les fiches, et de relire nos textes. Nous avons retenu : les scripts après vérification de leurs "
        "sorties contre les publications (totaux nationaux, taux du tableau I.8, base principale du challenge) ; les tableaux du post-primaire, de "
        "l'ACLED, de la pauvreté et du RGPH extraits avec ChatGPT, après contrôle. Nous avons écarté : les tableaux historiques dont la "
        "répartition par sexe était fausse, et toute affirmation non vérifiable dans une source. Les choix de méthode (mesure corrigée, règle de "
        "disponibilité de l'information, profils, actions) sont ceux de l'équipe.")

for st in d.paragraphs:
    pass
out = ROOT / "05_interpretation" / f"{TEAM}_05-interpretation_D1_analyst_documentation_v1.docx"
pdf = enregistrer(d, out)
for f in tmp.glob("*"): f.unlink()
tmp.rmdir()
print(pdf.name if pdf else out.name)
