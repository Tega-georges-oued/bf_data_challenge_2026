# VIGIE-École – Solution, plan de travail et journal

Copie Markdown du document de référence (version en ligne, avec les schémas : https://claude.ai/artifact/4vwGHK8S6E6oM4R3viHa6d). Mise à jour : 16 novembre 2026. En cas d'écart, la version en ligne fait foi ; mettre cette copie à jour à la fin de chaque séance.

## Mode d'emploi pour reprendre le travail

Ce document est la référence unique du projet : toute personne ou tout outil d'IA qui reprend le travail le lit d'abord, en entier, puis ouvre le journal (dernière section).

1. Lire la solution, l'architecture et le plan (sections suivantes).
2. Ouvrir le journal : la ligne « en cours » dit où on s'est arrêté, la ligne « à faire » suivante dit quoi faire.
3. Travailler dans le dossier `BF_DATA_CHALLENGE` ; cette copie est tenue à jour dans `BF_DATA_CHALLENGE/00_PILOTAGE/PLAN_ET_JOURNAL.md`.
4. À la fin de chaque séance : mettre à jour le journal (fait, en cours, décisions, usage de l'IA).

**Règles qui ne se discutent pas**

- **17 régions et 47 provinces partout.** Les sources sur les 13 anciennes régions ne servent que d'entrées : elles sont converties au niveau de la commune ou de la province (codes géographiques COD-AB, `adm3_pcode_old` → `adm3_pcode`) avant toute analyse. Aucun résultat, aucune carte, aucune fiche n'est livré sur 13 régions.
- **Citer la source** de chaque donnée : producteur, publication, année, date d'extraction.
- **Aucune donnée sensible** (élèves, données nominatives) n'est envoyée à un outil d'IA ; l'IA ne voit que des chiffres agrégés publics. Chaque usage de l'IA est noté dans le journal (règle du challenge).
- **Nommage des dépôts** : `EQUIPE_ÉTAPE_D1_RÔLE_description_vN`, sans espace ni accent, un fichier par étape, un LISEZ-MOI par dépôt.
- **Aucun résultat simulé** : ce qui n'est pas calculé sur des données réelles est présenté comme une perspective.

**Arborescence de travail**

| Dossier | Contenu |
| --- | --- |
| `DATAS/` | Données reçues et téléchargées, jamais modifiées (`DATAS/Sources_externes/` pour les sources hors Data Pack) |
| `00_PILOTAGE/` | Cette copie, journal, référentiel géographique |
| `01_collecte` à `05_interpretation` | Un dossier par étape du challenge, tel que déposé sur la plateforme |
| `app/` | Code de l'application et du moteur |

## La solution : VIGIE-École

VIGIE-École est un système d'alerte précoce qui dit, pour chacune des 47 provinces et des 17 régions, où le décrochage va frapper, pourquoi, et où agir en priorité avec les moyens disponibles.

**Le problème, avec nos mots.** Le taux d'abandon publié arrive un an après les faits et mélange trois choses : les vrais abandons, les sorties forcées par la fermeture d'écoles et les élèves déplacés réinscrits ailleurs. Un décideur ne peut donc ni anticiper, ni savoir quelle réponse donner à quel endroit.

**Notre question.** Comment repérer dès la rentrée, puis chaque mois, les provinces où le décrochage menace, en comprendre la cause dominante, et dire à chaque niveau de décision où et comment agir ?

| Brique | Ce qu'elle produit | Statut pour le 18/11 |
| --- | --- | --- |
| 1. Mesurer le vrai décrochage | Flux d'élèves par province, niveau et sexe (cohorte reconstituée), du CP1 à la terminale ; **taux d'abandon corrigé** des fermetures d'écoles et des déplacements ; carte « où l'école perd ses élèves » | Socle garanti |
| 2. Anticiper | Prévision à un an par province ; révision mensuelle à partir des signaux rapides (fermetures d'écoles, violences, déplacés) ; **test rétrospectif sur 2022-23** | Prévision annuelle garantie, test rétrospectif visé |
| 3. Décider où agir et comment | Typologie des provinces par cause dominante (insécurité, filles, orpaillage, pauvreté) ; grille « cause → actions » validée par le terrain ; **simulateur de ciblage** ; fiches d'une page pour les 17 régions | Typologie et fiches garanties, simulateur visé |

**Ce qui nous distingue**

- On corrige la mesure au lieu de modéliser un chiffre biaisé : abandon, sortie forcée et transfert sont distingués.
- On couvre le post-primaire par province grâce aux annuaires MESFPT, absents du Data Pack.
- On anticipe en cours d'année, et on le prouve sur 2022-23.
- On passe du « où » au « quoi faire, où, avec quels moyens », avec une grille d'actions écrite par un conseiller d'éducation.
- Tout est livré sur les 17 régions et 47 provinces.

## Architecture

VIGIE-École est un système d'information, pas une simple application : la valeur est dans la couche 1, qui se met à jour seule, l'application n'en est que la vitrine.

- **Couche 1 · Connecteurs et base harmonisée** : une ligne par province, par mois ou par année, par niveau et par sexe, sur 17 régions et 47 provinces.
- **Couche 2 · Moteur** : mesure corrigée (flux de cohorte, abandon corrigé) ; prévision (annuelle par province, révision mensuelle) ; explication (facteurs SHAP, typologie des causes) ; ciblage (où agir, avec quoi, grille d'actions).
- **Couche 3 · Application de décision** (Streamlit, hors ligne) : carte d'alerte, vue région, vue province, simulateur de ciblage, fiches PDF ; pour le niveau central (atlas, ciblage budgétaire), la direction régionale (fiche d'une page) et la province, la CEB, la commune (classement et alerte du mois).

| Vitesse | Sources | Comment elles arrivent | Rôle |
| --- | --- | --- | --- |
| Mensuelle | ACLED, Insecurity Insight, OIM, prix alimentaires, prévisions VIEWS ; rapports d'urgence éducative | Interfaces de données HDX et ACLED (mise à jour hebdomadaire programmée) ; rapports d'urgence en PDF, lus par OCR | Faire bouger le risque en cours d'année |
| Annuelle | Annuaires DGESS et MESFPT, projections de population, annuaires régionaux | Le nouvel annuaire est déposé dans une zone d'import, puis extrait et recalculé | Recaler les modèles, mesurer l'abandon réel |
| Quotidienne (à terme) | FASO SCHOOL TRACKER et logiciels de vie scolaire | Export pseudonymisé ou interface de données par établissement | Descendre au niveau de l'élève |

**Référentiel géographique.** La commune est la brique commune aux deux découpages. Chaque donnée est rattachée à sa commune ou à son ancienne province, puis reportée sur les 47 provinces et 17 régions par la table COD-AB. Recommandation au ministère : un accès direct à la base du recensement scolaire de la DGESS, au lieu des PDF.

**Technique** : Python, base DuckDB ou Parquet (un fichier, sans serveur), Streamlit ; tout fonctionne sans connexion et se relance en une commande.

## Perspective : vers FASO SCHOOL TRACKER

VIGIE-École est la fonction « Analyser » de FASO SCHOOL TRACKER, démontrée dès aujourd'hui avec les données disponibles ; le challenge sert à prouver le besoin d'un système unifié, de la maternelle à l'université.

| Horizon | Système | Données | Alerte | Délai |
| --- | --- | --- | --- | --- |
| Aujourd'hui | VIGIE-École (challenge) | Annuaires PDF et signaux mensuels de contexte | Par province | 1 an, puis mensuel |
| Demain (après accès à la base de la DGESS) | VIGIE-École + base DGESS | Recensement scolaire en accès direct | Par établissement | Dès la rentrée |
| Après-demain (après avis de la CIL, établissements pilotes) | FASO SCHOOL TRACKER | Données élève, de la maternelle à l'université | Par élève | Au trimestre |

Seul un identifiant unique de l'apprenant permet de savoir si un élève « disparu » des statistiques a abandonné, a été transféré ou a été déplacé ; notre mesure corrigée le montrera chiffres à l'appui.

- Un schéma de données commun (élève → établissement → commune → province → région) et une fiche « contrat de données ».
- Un onglet « Perspective » dans l'application et environ une page sur 15 dans la documentation, sans résultat simulé.
- Précautions : infrastructure publique souveraine (hébergement au Burkina, avis de la CIL, loi 001-2021), pas de volet commercial, pas de chiffres non sourcés, pas de promesse de fin de toute collecte (les facteurs de contexte restent externes).

## Plan de travail jusqu'au 18 novembre

Le plan livre chaque étape demandée par la commission le jour même où le travail technique la produit : un dépôt par étape, cinq dépôts du lundi soir au mercredi. Les tâches techniques T01 à T16 sont inchangées ; s'y ajoutent huit tâches de livrables (L01 à L08), qui documentent ce que les tâches techniques produisent déjà, sans les retarder.

Dépôt sur equation.africadataentry.com, clôture le 18 novembre (heure limite à confirmer). G = Georges (engineer, architect, scientist) ; CE = conseiller d'éducation (analyst côté terrain, fiches, présentation). Chaque fichier déposé porte son rôle dans son nom : `EQUIPE_ÉTAPE_D1_RÔLE_description_vN`.

**Correspondance entre livrables demandés et tâches**

| Livrable demandé | Rôle | Dépôt | Tâches | Quand |
| --- | --- | --- | --- | --- |
| Données brutes référencées | Engineer | D1 · 01_collecte | T02, T03, L01 | Lundi soir |
| Données propres et journal de nettoyage | Engineer | D2 · 02_nettoyage | T04, T06, L02 | Mardi midi (v1), mardi soir (v2 avec le post-primaire) |
| Schéma des données, dictionnaire des variables, plan du parcours | Architect | D3 · 03_transformation | T07, T08, L03, L04, L05 | Mardi après-midi |
| Indicateurs, code du modèle, mesure de fiabilité, prévisions | Scientist et analyst | D4 · 04_analyse | T09, T10, T12, L06 | Mardi soir (v1), mercredi midi (v2 avec typologie et facteurs) |
| Carte d'alerte, tableau de bord, fiches d'une page | Analyst | D5 · 05_interpretation | T13, T14 | Mercredi |
| Solution utilisable et relançable | Équipe | D5 | T13, T16 | Mercredi |
| Documentation de 15 pages | Équipe | D5 | L07 (au fil de l'eau), T15 (assemblage) | Parties rédigées du lundi au mercredi |
| LISEZ-MOI de chaque dépôt | Équipe | D1 à D5 | L08 | À chaque dépôt |

**Lundi 16 novembre – référentiel et collecte**

- [x] T01 · G · Arborescence `00_PILOTAGE`, `01_collecte` à `05_interpretation`, `app/` et cette copie
- [x] T02 · G · Référentiel géographique : commune → province → région (17 régions, 47 provinces), avec l'ancien code de chaque commune
- [x] T03 · G · Re-télécharger les sources externes perdues dans `DATAS/Sources_externes`
- [x] T04 · G · Annuaires du primaire 2017-18 à 2024-25 : effectifs par province, niveau et sexe ; redoublants ; taux de promotion, redoublement et abandon
- [~] T05 · CE · (première version dans app/data/grille_actions.csv, à valider par le CE) · Grille « cause dominante → actions possibles » par niveau de décision
- [x] L01 · G · Registre des sources (producteur, publication, année, lien, date d'extraction), rempli pendant T03
- [x] L02 · G · Journal de nettoyage, tenu pendant T04 puis T06 (correction, raison, lignes touchées)
- [x] L07 · CE · Documentation partie 1 et brouillon de la partie 6 · G · partie 2

**Dépôt D1 (lundi soir) · 01_collecte** : données brutes référencées, registre des sources, référentiel géographique, LISEZ-MOI.

**Mardi 17 novembre – mesure, facteurs et modèle**

- [x] T06 · G · Annuaires post-primaire et secondaire (MESFPT, 2018-19 à 2024-25) : effectifs et redoublants par province ; trou de 2023-24 signalé
- [x] T07 · G · Flux de cohorte et taux d'abandon corrigé ; contrôle des totaux
- [x] T08 · G · Table des facteurs par province et par année
- [x] T09 · G · Modèle : reconduction, régression régularisée, gradient boosting ; validation en retirant une année à la fois ; calibration ; équité filles-garçons
- [x] T10 · G · Test rétrospectif (fait sur 2021-22, l'année de crise, avec les données de la rentrée 2022)
- [ ] T11 · CE · (à faire : relire les 17 fiches et la grille) · Contrôle de cohérence terrain ; contenu des fiches
- [x] L03 · G · Schéma des données (tables, clés), figé après T07 et T08
- [x] L04 · G · Dictionnaire des variables (nom, définition, unité, source, calcul)
- [x] L05 · G · Plan du parcours des données (sources → dépôts → application)
- [x] L06 · G · Rapport de fiabilité (gain sur la reconduction, erreurs par année retirée, calibration, équité, test 2022-23)
- [x] L07 · G · Documentation parties 3 et 4

**Dépôt D2 (mardi midi, v2 le soir) · 02_nettoyage** : effectifs du primaire propres, puis du post-primaire, journal de nettoyage, LISEZ-MOI.

**Dépôt D3 (mardi après-midi) · 03_transformation** : base harmonisée, schéma, dictionnaire, plan du parcours, LISEZ-MOI.

**Dépôt D4 v1 (mardi soir) · 04_analyse** : code du modèle, prévisions par province, rapport de fiabilité, LISEZ-MOI.

**Mercredi 18 novembre – restitution et dépôts**

- [x] T12 · G · Typologie, explication des facteurs (SHAP), simulateur de ciblage
- [x] T13 · G · Application Streamlit
- [x] T14 · CE + G · Fiches d'une page pour les 17 régions et atlas national
- [x] T15 · CE + G · Documentation de 15 pages (assemblage, puis parties 5 à 7)
- [x] T16 · G · Nommage, LISEZ-MOI et dépôts ; relance de l'application en une commande
- [x] L07 · CE + G · Documentation parties 5, 6 (finale) et 7
- [x] L08 · G · LISEZ-MOI général des cinq dépôts et de leurs versions

**Dépôt D4 v2 (mercredi midi) · 04_analyse** : typologie et explication des facteurs ajoutées.

**Dépôt D5 (mercredi) · 05_interpretation** : application, fiches des 17 régions, atlas, documentation, LISEZ-MOI général.

**Si l'équipe est retenue (20 et 21 novembre)** : présentation, démonstration, extensions non terminées.

## Risques et parades

| Risque | Parade |
| --- | --- |
| L'extraction des annuaires prend trop de temps | Primaire d'abord ; post-primaire au niveau régional si pas prêt mardi soir, et c'est écrit |
| Données seulement sur les 13 anciennes régions | Conversion par province ou commune ; un chiffre seulement par ancienne région sert au contrôle, jamais à une carte ou une fiche |
| Une province ancienne partagée entre deux nouvelles | Répartition par la population des communes (recensement 2019), méthode signalée |
| Peu d'années pour apprendre (environ 8) | Modèles simples et régularisés, intervalles d'incertitude |
| Rapports d'urgence lus par OCR | Contrôle des valeurs extrêmes sur le PDF ; mois illisibles marqués manquants |
| Trou de l'annuaire post-primaire 2023-24 | Interpolation ou tableau de bord, signalé |
| Simulateur de ciblage pas fini | Présenté dans l'onglet Perspective, sans résultat chiffré |

## Journal

Dernière mise à jour le 16 novembre au soir : toutes les tâches techniques et tous les livrables D1 à D5 sont faits et déposés. Reste au conseiller d'éducation : valider la grille d'actions (T05) et relire les fiches (T11).

**En cours** : validation terrain par le CE (T05, T11). Si des actions changent : modifier app/data/grille_actions.csv puis `python app/relancer.py --depuis t14`.

**Fait**

| Date | Quoi | Résultat |
| --- | --- | --- |
| 16/11 | Reprise et vérification du travail fait avec ChatGPT | Retenus après contrôle : tableaux détaillés du primaire 2017-18 à 2024-25 (387 cases sur 390 identiques à la base principale), taux publiés du post-primaire, ACLED par mois, pauvreté, RGPH par commune, PDI. Écartée : la répartition par sexe des tableaux historiques 2024-25 |
| 16/11 | T02-T03 – référentiel et registre | 351 communes (population 20 505 155 = RGPH), passage 45 → 47 provinces, registre de 248 fichiers |
| 16/11 | T04-T04b – primaire 2008-09 à 2024-25 | Série consolidée v2, journaux et contrôles dans 02_nettoyage |
| 16/11 | T07-T08 – mesure et facteurs | Abandon publié (vérifié contre le tableau I.8), effet des fermetures, abandon corrigé ; table d'analyse 47 provinces × 17 ans |
| 16/11 | T09-T12 – modèle | Gradient boosting : erreur −14,2 % contre la reconduction ; erreur médiane 2 pts (zones calmes), 15 pts (zones à fort défi sécuritaire) ; prévision 2024-25 : 10,3 %, ≈ 305 000 élèves ; SHAP ; 4 profils régionaux |
| 16/11 | T13 – application | Streamlit hors connexion, 8 pages, carte sans fond de carte en ligne |
| 16/11 | T14-T16, L03-L08 | 17 fiches, atlas 8 p., documentation 8 p. (Word + PDF), schéma, parcours, dictionnaire (115 variables), rapport de fiabilité, LISEZ-MOI, `app/relancer.py` |
| 16/11 | T01 – arborescence et cette copie | Dossiers créés dans `BF_DATA_CHALLENGE` |
| 16/11 | Solution et plan de travail arrêtés | Document de référence en ligne et cette copie |
| 16/11 | Inventaire des annuaires ajoutés par Georges | 58 PDF : 43 déjà dans le Data Pack, 15 nouveaux (MESFPT : 6 annuaires post-primaire et secondaire, 8 tableaux de bord, 1 annuaire formation professionnelle). Effectifs et redoublants par province, pas les abandons. |
| 13/11 | Sources externes (Open Data for Africa, HDX) | 21 fichiers téléchargés, 2 seulement arrivés dans `DATAS` ; 19 à re-télécharger (T03). Microdonnées INSD sous licence. |
| 13/11 | Prise de connaissance du dossier | Scénario territoire ; base principale par ancienne région ; abandons par province dans les annuaires |

**Décisions**

| Date | Décision |
| --- | --- |
| 16/11 | Trois mesures de l'abandon : publiée (DGESS), sortie nette, corrigée des fermetures ; correction signalée fragile si le nombre d'écoles varie de plus de 10 % |
| 16/11 | Prévision du primaire seulement ; post-primaire mesuré, pas prévu (trop peu d'années) |
| 16/11 | Règle de disponibilité : seules les données connues à la rentrée servent à la prévision |
| 16/11 | Dans les zones à fort défi sécuritaire, la carte sert à classer, pas à donner un chiffre exact (dit dans l'application, les fiches et la documentation) |
| 16/11 | Plan calé sur les livrables : cinq dépôts D1 à D5 et tâches L01 à L08, sans toucher aux tâches techniques |
| 16/11 | Tout le travail du challenge est sur 17 régions et 47 provinces |
| 16/11 | FASO SCHOOL TRACKER = perspective centrale, infrastructure publique, sans volet commercial ni chiffres non sourcés |
| 16/11 | Système en trois couches et trois vitesses de données |
| 13/11 | Prévision par province, primaire + post-primaire + secondaire |

**Questions ouvertes**

- Code d'équipe attribué par la plateforme (nommage `EQUIPE_...`) ?
- Heure limite exacte des dépôts le 18 novembre ?

**Usage de l'IA**

| Date | Outil | Ce qui a été demandé | Ce qui a été retenu |
| --- | --- | --- | --- |
| 13-16/11 | Claude (Cowork) | Lecture du dossier, recherche et téléchargement de sources publiques, comparaison des annuaires, propositions de solution, rédaction du plan | Inventaire des sources, solution combinée, plan ; décisions prises par l'équipe |
| 16/11 | ChatGPT | Extraction de tableaux des annuaires et des sources externes, premiers livrables | Les tableaux vérifiés listés ci-dessus ; le reste refait ou écarté |
| 16/11 | Claude (Cowork) | Vérification du travail ChatGPT, scripts de la chaîne, modèle, application, fiches, atlas, documents | Résultats contrôlés contre les publications ; choix de méthode faits par l'équipe |
