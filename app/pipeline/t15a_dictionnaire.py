"""L04 - Dictionnaire des variables des dépôts 03_transformation et 04_analyse (généré à partir des fichiers).

Usage : python t15a_dictionnaire.py [--racine CHEMIN_BF_DATA_CHALLENGE]
Sortie : 03_transformation/VIGIE-Ecole-Team_03-transformation_D1_architect_dictionnaire-variables_v1.csv
"""
import argparse
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[2])
ROOT = ap.parse_args().racine

ANN = "Annuaires statistiques MEBAPLN-DGESS (primaire)"
MES = "Annuaires statistiques MESFPT-DGESS (post-primaire et secondaire), tableau II.3.11"
RG = "INSD, RGPH 2019 (synthèse et volume 3 Cartographie de la pauvreté)"
AC = "ACLED, événements Burkina Faso (extraction novembre 2026)"
CO = "CONASUR, personnes déplacées internes par commune (via HDX)"
GEO = "IGB/OCHA COD-AB Burkina Faso (17 régions, 47 provinces, 351 communes)"
MOD = "Calcul VIGIE-École (04_analyse, t09_modele.py)"
CALC = "Calcul VIGIE-École"

# nom : (définition, unité, source, calcul)
D = {
 "old_adm2_pcode": ("Code d'une des 45 anciennes provinces (avant 2025)", "code", GEO, "adm2_pcode_old des communes COD-AB"),
 "adm1_pcode": ("Code de la région (découpage 2025, 17 régions)", "code", GEO, ""),
 "adm1_name": ("Nom de la région (17 régions)", "texte", GEO, ""),
 "adm2_pcode": ("Code de la province (découpage 2025, 47 provinces)", "code", GEO, ""),
 "adm2_name": ("Nom de la province (47 provinces)", "texte", GEO, ""),
 "pays": ("Pays", "texte", "", ""),
 "annee_depart": ("Année scolaire t au cours de laquelle l'abandon se produit", "AAAA/AAAA", ANN, "L'abandon de l'année t est mesuré par l'annuaire t+1"),
 "annee_arrivee": ("Année scolaire t+1 utilisée pour mesurer l'abandon", "AAAA/AAAA", ANN, ""),
 "an": ("Première année civile de annee_depart (clé numérique)", "année", CALC, ""),
 "sexe": ("T ensemble, F filles, G garçons", "code", ANN, ""),
 "effectif_cp1_cm1": ("Élèves inscrits de CP1 à CM1 en année t", "élèves", ANN, "Somme des effectifs CP1 à CM1 (le CM2 est exclu : sortie par examen)"),
 "sorties_nettes": ("Élèves ni promus ni redoublants en t+1 (méthode de la cohorte reconstituée, ISU/DGESS)", "élèves", CALC,
                    "Somme par niveau de E(g,t) - [E(g+1,t+1) - R(g+1,t+1)] - R(g,t+1)"),
 "sorties_positives": ("Sorties nettes en ramenant à 0 les valeurs négatives par niveau (convention DGESS)", "élèves", CALC, "max(0, sortie) par niveau, puis somme"),
 "abandon_CP1_pct": ("Taux d'abandon en CP1 (convention DGESS)", "%", CALC, "100 x sortie positive CP1 / effectif CP1"),
 "abandon_CP2_pct": ("Taux d'abandon en CP2", "%", CALC, "idem"), "abandon_CE1_pct": ("Taux d'abandon en CE1", "%", CALC, "idem"),
 "abandon_CE2_pct": ("Taux d'abandon en CE2", "%", CALC, "idem"), "abandon_CM1_pct": ("Taux d'abandon en CM1", "%", CALC, "idem"),
 "ecoles_depart": ("Écoles primaires en année t", "écoles", ANN + ", tableau I.1", "Disponible depuis 2017-18"),
 "ecoles_arrivee": ("Écoles primaires en année t+1", "écoles", ANN + ", tableau I.1", ""),
 "choc_ecoles": ("Variation relative du nombre d'écoles entre t et t+1", "ratio", CALC, "1 - ecoles_arrivee / ecoles_depart (positif = fermetures)"),
 "effet_fermetures": ("Élèves sortis du fait des fermetures (négatif : retours dans les écoles rouvertes)", "élèves", CALC, "effectif_cp1_cm1 x choc_ecoles"),
 "taux_abandon_dgess": ("Taux d'abandon du primaire CP1-CM1, convention DGESS (variable prévue)", "%", CALC,
                        "100 x sorties_positives / effectif_cp1_cm1 ; vérifié contre le tableau I.8 des annuaires"),
 "taux_sortie_nette": ("Taux de sortie nette, signé (peut être négatif en cas de retours)", "%", CALC, "100 x sorties_nettes / effectif_cp1_cm1"),
 "taux_effet_fermetures": ("Part des élèves sortis à cause des fermetures d'écoles", "points de %", CALC, "100 x effet_fermetures / effectif_cp1_cm1"),
 "taux_abandon_corrige": ("Abandon corrigé des fermetures et réouvertures d'écoles (estimation)", "%", CALC,
                          "100 x max(0, sorties_nettes - effet_fermetures) / effectif_cp1_cm1 ; fragile si |taux_effet_fermetures| > 10"),
 "taux_abandon_post_primaire": ("Taux d'abandon du post-primaire (moyenne 6e, 5e, 4e ; 3e exclue : classe d'examen)", "%", MES,
                                "Taux publiés par province, édition t+1 = transition t vers t+1 ; pondération par effectifs pour agréger"),
 "taux_abandon_secondaire": ("Taux d'abandon du secondaire (moyenne 2nde, 1re ; Tle exclue)", "%", MES, "idem"),
 "taux_abandon_dgess_filles": ("Taux d'abandon DGESS des filles", "%", CALC, ""), "taux_abandon_corrige_filles": ("Abandon corrigé des filles", "%", CALC, ""),
 "taux_abandon_dgess_garcons": ("Taux d'abandon DGESS des garçons", "%", CALC, ""), "taux_abandon_corrige_garcons": ("Abandon corrigé des garçons", "%", CALC, ""),
 "ligne_prevision": ("Vrai pour la ligne à prévoir (2024-25), dont l'abandon n'est pas encore publié", "booléen", CALC, ""),
 "part_filles_primaire": ("Part des filles parmi les élèves du primaire, année t", "%", ANN, ""),
 "taux_redoublement_primaire": ("Redoublants du primaire / élèves du primaire, année t", "%", ANN, "100 x redoublants / effectif"),
 "eleves_par_maitre": ("Élèves par maître chargé de cours, année t", "élèves", ANN + ", tableau I.1", ""),
 "eleves_par_salle": ("Élèves par salle de classe, année t", "élèves", ANN + ", tableau I.1", ""),
 "eleves_pour_1000_hab": ("Élèves du primaire pour 1 000 habitants (population 2019)", "pour 1 000", ANN + " ; " + RG, ""),
 "acled_evenements_civils_12m": ("Violences contre les civils, octobre t à septembre t+1 (12 mois de l'année scolaire prévue)", "événements", AC,
                                 "Fenêtre de 12 mois disponible au moment de la prévision"),
 "acled_evenements_violence_12m": ("Événements violents (batailles, explosions, violences contre les civils), 12 mois", "événements", AC, ""),
 "acled_deces_civils_12m": ("Décès lors de violences contre les civils, 12 mois", "décès", AC, ""),
 "acled_deces_violence_12m": ("Décès lors d'événements violents, 12 mois", "décès", AC, ""),
 "acled_ev_violence_3m_rentree": ("Événements violents de juillet à septembre (avant la rentrée)", "événements", AC, ""),
 "acled_ev_violence_12m_precedents": ("Événements violents des 12 mois précédents", "événements", AC, ""),
 "acled_variation_violence": ("Variation des événements violents d'une année sur l'autre", "ratio", AC, ""),
 "acled_evenements_violence_12m_p100k": ("Événements violents pour 100 000 habitants, 12 mois", "pour 100 000", AC + " ; " + RG, ""),
 "acled_deces_violence_12m_p100k": ("Décès liés aux violences pour 100 000 habitants, 12 mois", "pour 100 000", AC + " ; " + RG, ""),
 "acled_evenements_civils_12m_p100k": ("Violences contre les civils pour 100 000 habitants, 12 mois", "pour 100 000", AC + " ; " + RG, ""),
 "pdi_pour_1000_hab": ("Personnes déplacées internes pour 1 000 habitants (dernier relevé avant la rentrée)", "pour 1 000", CO + " ; " + RG, ""),
 "pdi_couverture_communes": ("Part des communes de la province renseignées dans le relevé", "ratio", CO, ""),
 "pdi_date_releve": ("Date du relevé CONASUR utilisé", "date", CO, ""),
 "rgph2019_hors_ecole_6_11ans": ("Enfants de 6-11 ans hors de l'école", "%", RG, "Agrégé des communes par population"),
 "rgph2019_hors_ecole_12_15ans": ("Enfants de 12-15 ans hors de l'école", "%", RG, ""),
 "rgph2019_emploi_7_14ans": ("Taux d'emploi des enfants de 7-14 ans", "%", RG, ""),
 "rgph2019_filles_17ans_deja_mariees": ("Filles de 17 ans déjà mariées", "%", RG, ""),
 "rgph2019_alphabetisation_15_64ans": ("Taux d'alphabétisation des 15-64 ans", "%", RG, ""),
 "rgph2019_electricite": ("Ménages ayant accès à l'électricité", "%", RG, ""),
 "rgph2019_acte_naissance": ("Enfants disposant d'un acte de naissance", "%", RG, ""),
 "rgph2019_parite_primaire": ("Indice de parité filles/garçons de fréquentation au primaire", "indice", RG, ""),
 "rgph2019_frequentation_nette_postprimaire": ("Taux net de fréquentation au post-primaire (12-15 ans)", "%", RG, ""),
 "rgph2019_incidence_pauvrete": ("Incidence de la pauvreté monétaire (seuil 2018 : 194 624 FCFA par personne et par an)", "%", RG + " (estimation sur petits domaines, EHCVM 2018)",
                                 "Soum et Tapoa répartis par population des communes"),
 "part_eleves_plus_5km": ("Part des élèves habitant à plus de 5 km de l'école", "ratio", ANN + " (tableaux des distances)", ""),
 "Inertie scolaire": ("Contribution moyenne (SHAP) de la famille de facteurs à la prévision régionale", "points de %", MOD, "Moyenne pondérée par les effectifs"),
 "Insécurité et déplacements": ("idem, famille insécurité et déplacements", "points de %", MOD, ""),
 "Offre scolaire et distance": ("idem, famille offre scolaire et distance", "points de %", MOD, ""),
 "Pauvreté et travail des enfants": ("idem, famille pauvreté et travail des enfants", "points de %", MOD, ""),
 "Situation des filles": ("idem, famille situation des filles", "points de %", MOD, ""),
 "groupe": ("Numéro du groupe de régions (k-moyennes, 4 groupes)", "code", MOD, ""),
 "profil_regional": ("Libellé du profil régional selon les familles de facteurs dominantes", "texte", MOD, ""),
 "decile": ("Décile de la prévision", "1 à 10", MOD, ""), "prevision_moyenne": ("Prévision moyenne du décile", "%", MOD, ""),
 "observe_moyen": ("Abandon observé moyen du décile", "%", MOD, ""), "n": ("Nombre d'observations", "nombre", MOD, ""),
 "annee_test": ("Année prévue lors de la validation temporelle (avec les seules années antérieures)", "année", MOD, ""),
 "zone_securite": ("faible ou fort (fort : au moins 5 événements violents pour 100 000 habitants sur 12 mois)", "code", MOD, ""),
 "demi_largeur_80": ("Demi-largeur de l'intervalle à 80 % (méthode conforme, 3 années précédentes)", "points de %", MOD, ""),
 "couverture": ("Part des valeurs observées tombées dans l'intervalle à 80 %", "ratio", MOD, ""),
 "mae": ("Erreur absolue moyenne", "points de %", MOD, ""), "rmse": ("Racine de l'erreur quadratique moyenne", "points de %", MOD, ""),
 "biais_moyen": ("Prévu moins observé, en moyenne", "points de %", MOD, ""),
 "spearman": ("Corrélation de rang entre prévu et observé", "-1 à 1", MOD, ""),
 "part_abandons_captee_top10pct": ("Part des abandons observés situés dans les 10 % de provinces au risque prévu le plus élevé", "ratio", MOD, ""),
 "rappel_top10pct": ("Part des provinces du top 10 % observé retrouvées dans le top 10 % prévu", "ratio", MOD, ""),
 "facteur": ("Nom technique de la variable explicative", "texte", MOD, ""), "libelle": ("Libellé en clair du facteur", "texte", MOD, ""),
 "famille": ("Famille de facteurs", "texte", MOD, ""), "contribution_points": ("Contribution SHAP du facteur à la prévision de la province", "points de %", MOD, ""),
 "shap_moyen_absolu_points": ("Contribution absolue moyenne du facteur sur toutes les prévisions", "points de %", MOD, ""),
 "modele": ("Modèle : reconduction, ridge ou gbm (gradient boosting)", "texte", MOD, ""),
 "prevision": ("Abandon prévu au primaire pour 2024-25 (modèle retenu)", "%", MOD, ""),
 "intervalle_80_bas": ("Borne basse de l'intervalle à 80 % (bornée à 0)", "%", MOD, ""), "intervalle_80_haut": ("Borne haute de l'intervalle à 80 %", "%", MOD, ""),
 "prevision_gbm": ("Prévision du gradient boosting", "%", MOD, ""), "prevision_ridge": ("Prévision de la régression ridge", "%", MOD, ""),
 "prevision_reconduction": ("Taux de l'année précédente reconduit", "%", MOD, ""),
 "niveau_alerte": ("rouge : 20 % des provinces au risque le plus élevé ; orange : au-dessus de la médiane ; jaune : sinon", "code", MOD, ""),
 "effectif_cp1_cm1_2024": ("Élèves CP1-CM1 en 2024-25", "élèves", ANN, ""),
 "decrocheurs_attendus": ("Élèves qui risquent d'abandonner en 2024-25", "élèves", MOD, "prevision / 100 x effectif_cp1_cm1_2024"),
 "abandon_observe_2023_24": ("Abandon DGESS observé en 2023-24", "%", CALC, ""), "abandon_corrige_2023_24": ("Abandon corrigé observé en 2023-24", "%", CALC, ""),
 "attendu_selon_profil": ("Abandon attendu selon le seul profil structurel de la province (sans inertie), 2023-24", "%", MOD, "Régression ridge sur les facteurs structurels"),
 "ecart_au_risque_attendu": ("Observé moins attendu selon le profil (positif : la province fait moins bien que son profil)", "points de %", MOD, ""),
 "cause_dominante": ("Famille de facteurs à la contribution positive la plus forte", "texte", MOD, ""),
 "trois_facteurs_principaux": ("Les trois facteurs qui augmentent le plus le risque prévu", "texte", MOD, ""),
 "observe": ("Abandon observé (validation)", "%", CALC, ""), "pred_reconduction": ("Prévision par reconduction (validation)", "%", MOD, ""),
 "pred_ridge": ("Prévision ridge (validation)", "%", MOD, ""), "pred_gbm": ("Prévision gradient boosting (validation)", "%", MOD, ""),
 "modele_cible": ("Variable prévue", "texte", MOD, ""),
}
for c in ["retard_taux_abandon_dgess", "retard_taux_abandon_corrige", "retard_taux_sortie_nette", "retard_taux_effet_fermetures",
          "retard_taux_abandon_post_primaire", "retard_taux_abandon_secondaire"]:
    base = c.replace("retard_", "")
    D[c] = (f"Valeur de {base} l'année précédente (t-1), connue à la rentrée de l'année prévue", D[base][1], D[base][2], "Décalage d'un an par province")

rows = []
for f in sorted(list((ROOT / "03_transformation").glob("*.csv")) + list((ROOT / "04_analyse").glob("*.csv"))):
    if "dictionnaire" in f.name:
        continue
    for c in pd.read_csv(f, sep=";", nrows=2).columns:
        d = D.get(c, ("", "", "", ""))
        rows.append({"fichier": f.name, "variable": c, "definition": d[0], "unite": d[1], "source": d[2], "calcul": d[3]})
out = pd.DataFrame(rows)
manq = out[out.definition == ""].variable.unique()
assert len(manq) == 0, manq
p = ROOT / "03_transformation" / "VIGIE-Ecole-Team_03-transformation_D1_architect_dictionnaire-variables_v1.csv"
out.to_csv(p, sep=";", index=False, encoding="utf-8-sig")
print(len(out), "lignes,", out.variable.nunique(), "variables ->", p.name)
