# Sources externes – VIGIE-École (Défi 1) – téléchargées le 13/11/2026

Tous les fichiers sont préfixés `DCB_ext_` (dossier Téléchargements de Chrome). Format CSV : séparateur `;`, UTF-8.

## 1. Open Data for Africa – Burkina Faso (burkinafaso.opendataforafrica.org, INSD)
Extraction via l'API publique du portail ; une ligne = une valeur (jeu, dimensions, année, valeur, unité, source).
Le détail des 339 jeux (identifiant, titre, source, URL) est dans `DCB_ext_ODA_catalogue_jeux_telecharges.csv`.

| Fichier | Contenu | Intérêt pour le Défi 1 |
|---|---|---|
| `DCB_ext_ODA_statut_scolaire_6_16ans_RGPH2019.csv` | 29 jeux, monographies régionales RGPH 2019 : population de 6-16 ans par commune, par statut (jamais scolarisé / **déscolarisé** / scolarisé), par sexe et par milieu | **Stock de décrocheurs par commune**, une cible ou une variable de validation à la maille la plus fine |
| `DCB_ext_ODA_grossesses_milieu_scolaire.csv` | 12 jeux : cas de grossesses en milieu scolaire par province et par niveau | Facteur « filles » cité dans la note |
| `DCB_ext_ODA_mariages_precoces_forces_enfants.csv` | 43 jeux : victimes de mariages précoces ou forcés par province (action sociale) | Facteur « filles » |
| `DCB_ext_ODA_orpaillage_permis_or.csv` | Permis et autorisations d'exploitation artisanale d'or par région | Proxy de l'orpaillage |
| `DCB_ext_ODA_insecurite_fermetures_alimentaire.csv` | Établissements fermés pour insécurité, insécurité alimentaire | Sorties forcées / contexte |
| `DCB_ext_ODA_indicateurs_educ_province_region.csv` | 153 jeux : TBA, TBS, taux d'achèvement, redoublement, CEP et BEPC par province ou région (annuaires régionaux) | Séries par province, notamment pour le post-primaire |
| `DCB_ext_ODA_effectifs_ecoles_primaire_commune.csv` | 93 jeux : élèves, écoles, salles (dont salles sous paillote) et enseignants du primaire par commune | Variables par commune |

Limite : deux jeux de type « plat » (incidence de la pauvreté selon le chef de ménage ; travail des enfants) ne sont pas lisibles par l'API et n'ont pas été extraits.

## 2. HDX (data.humdata.org)
| Fichier | Producteur | Contenu |
|---|---|---|
| `DCB_ext_HDX_MENA_liste-ecoles-primaires-publiques_2016-2017.xlsx` | MENA | Liste des écoles primaires publiques 2016-17 (niveau établissement) |
| `DCB_ext_HDX_ACLED_violence-politique_admin2_mois_2026-11-11.xlsx` | ACLED | Événements et victimes de violence politique par province et par mois |
| `DCB_ext_HDX_ACLED_violence-civils_admin2_mois_2026-11-11.xlsx` | ACLED | Violences ciblant les civils par province et par mois |
| `DCB_ext_HDX_InsecurityInsight_education-in-danger_BFA_2017-2026.xlsx` | Insecurity Insight | Incidents contre l'éducation (écoles, enseignants, élèves) |
| `DCB_ext_HDX_InsecurityInsight_incendies-ecoles-Sahel_2020-2023.xlsx` | Insecurity Insight | Incendies d'écoles au Sahel |
| `DCB_ext_HDX_DHS_indicateurs-education_regions.csv`, `..._genre_...`, `..._quickstats_...`, `..._orphelins_...`, `..._alphabetisation_...` | DHS Program | Indicateurs EDS par région (fréquentation scolaire, mariage précoce, orphelins…) |
| `DCB_ext_HDX_OPHI_MPI_regions.csv` | OPHI | Pauvreté multidimensionnelle |
| `DCB_ext_HDX_OIM-DTM_deplaces_admin0-2.csv` | OIM DTM | Déplacés par province |
| `DCB_ext_HDX_VIEWS_previsions-conflit_priogrid_mois.csv` | VIEWS (Uppsala) | Prévisions mensuelles de conflit par cellule de grille (variable prospective) |

## 3. Visités, sans téléchargement
- **microdata.insd.bf** : 46 études (EDS 2021, EHCVM 2018 et 2021, RGPH…), toutes « fichiers sous licence ». L'accès demande un compte et une demande nominative à l'INSD (contact du challenge : Ibrahim OUATTARA). Les rapports agrégés sont déjà dans le Data Pack.
- **insd.bf** : ses publications (annuaires, RGPH, EHCVM) sont déjà dans le Data Pack.

À citer dans la documentation : producteur, publication, année et date d'extraction (13/11/2026).
