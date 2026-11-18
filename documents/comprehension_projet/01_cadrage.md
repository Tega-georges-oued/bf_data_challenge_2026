# Comprendre VIGIE-École — 1. Le cadrage

État examiné : 17 novembre 2026. Support de compréhension et de préparation aux questions ; ce document ne remplace pas le rapport final du challenge.

## 1. Le problème auquel nous répondons

Le Défi 1 demande de cartographier et d'anticiper le risque de décrochage scolaire par région. Pour un responsable éducatif, la question pratique est : **quels territoires examiner en priorité, avec quelles informations et quelles incertitudes ?**

Notre réponse repose sur des statistiques agrégées. Nous comparons les provinces, nous présentons une synthèse régionale et nous proposons des pistes d'action. Nous n'identifions pas des élèves individuels.

### Une formulation possible à l'oral

> VIGIE-École transforme des données éducatives et des données de contexte en un outil de repérage territorial. Il permet d'examiner l'évolution de l'abandon, de comparer les provinces et les régions, et d'estimer un taux encore non observé dans nos sources. L'outil présente aussi ses erreurs et ses limites pour éclairer une décision humaine.

## 2. Ce que nous cherchons à accomplir

| Objectif | Réalisation dans le projet | Limite à annoncer |
|---|---|---|
| Rendre les sources comparables | Nettoyage et référentiel géographique commun | Certaines valeurs sont estimées lors du passage géographique |
| Décrire l'abandon scolaire | Indicateurs provinciaux, régionaux et nationaux | Des données agrégées ne retracent pas tous les parcours individuels |
| Examiner l'effet des fermetures | Indicateur corrigé et comparaison avec l'indicateur DGESS | La correction repose sur une approximation, pas sur le suivi de chaque élève |
| Estimer un taux inconnu | Modèle statistique au primaire, comparé à deux références | Une estimation comporte une erreur et dépend des données disponibles |
| Orienter l'examen des territoires | Carte, fiches, atlas, facteurs associés et simulateur de ciblage | Les effets des interventions ne sont pas mesurés par le modèle |

## 3. Notre périmètre effectif

| Dimension | Périmètre actuel |
|---|---|
| Territoire | Burkina Faso ; restitution selon le référentiel utilisé par le projet : 17 régions, 47 provinces, 351 communes |
| Unité principale du modèle | Une province pour une année/transition scolaire |
| Prévision principale | Abandon au primaire, sur les classes CP1 à CM1 |
| Autres niveaux | Analyse des indicateurs publiés du post-primaire et du secondaire ; pas de modèle prédictif final retenu pour ces niveaux |
| Élèves concernés | Effectifs agrégés ; absence de score individuel d'élève |
| Validation du modèle | Années de test 2015 à 2023, avec apprentissage sur les années antérieures à chacune |
| Dernière estimation livrée | Sortie étiquetée 2024-2025 ; calendrier détaillé ci-dessous |

Le CM2 est exclu du calcul principal des sorties CP1-CM1 pour ne pas assimiler automatiquement une sortie de fin de cycle à un abandon. Ce choix doit être expliqué comme une délimitation du calcul, et non comme la preuve qu'aucun abandon n'existe en CM2.

Les communes servent notamment à établir les correspondances géographiques et certains facteurs de contexte. **Nous ne livrons pas un modèle de risque propre à chaque commune.**

## 4. Trois notions à ne pas confondre

| Notion | Ce qu'elle représente ici | Ce qu'elle ne prouve pas |
|---|---|---|
| Taux d'abandon selon la convention DGESS | Sorties reconstituées à partir des effectifs, promotions et redoublements entre deux années, avec les règles appliquées dans le pipeline | Le devenir exact de chaque élève sorti des effectifs |
| Sortie nette | Bilan agrégé des sorties et des arrivées ; certaines valeurs peuvent être négatives | Une liste nominative de décrocheurs |
| Abandon corrigé des fermetures/réouvertures | Estimation analytique retirant un effet approché lié à l'évolution du nombre d'écoles | Une mesure certaine du « véritable abandon », séparée de tous les déplacements et transferts |

**Le modèle principal livré prend pour cible le taux d'abandon selon la convention DGESS.** L'indicateur corrigé est présenté dans l'analyse et les graphiques ; les deux résultats ne doivent pas être interchangeables dans notre discours.

La formule de correction sera détaillée dans la fiche Transformation. L'hypothèse centrale est qu'une variation du nombre d'écoles entraîne un effet proportionnel sur les effectifs. Elle simplifie la réalité : les écoles n'ont pas toutes la même taille et les élèves peuvent se déplacer.

## 5. Quand la prévision est-elle faite ?

Les scripts `t08_facteurs.py` et `t09_modele.py` placent le point de prévision à la rentrée **t+1**, pour la transition étiquetée **t / t+1**.

Pour la sortie 2024-2025, le code utilise notamment des violences enregistrées d'octobre 2024 à septembre 2025. Le point de prévision revendiqué est donc la rentrée 2025. Le taux est considéré comme inconnu dans les données disponibles au projet et doit être mesuré à partir de l'annuaire suivant.

### Formulation correcte

> Il s'agit d'une estimation à la rentrée 2025 du taux associé à la transition 2024-2025, avant sa mesure dans les sources utilisées par le projet.

### Formulation à éviter

> Nous avons prévu dès la rentrée 2024 l'abandon de 2024-2025.

La seconde phrase serait incompatible avec les fenêtres de données présentes dans le code. Le dispositif actuel anticipe la disponibilité de la mesure ; il ne démontre pas une anticipation de tous les événements de l'année depuis son commencement. Le terme « anticipation » doit toujours être accompagné de la date de calcul et de la période cible.

**Point restant à vérifier lors de la fiche Analyse :** l'existence d'un découpage temporel du code ne suffit pas à prouver l'absence de fuite d'information. Les dates réelles de publication, les éventuelles révisions des données et l'usage rétrospectif du contexte RGPH 2019 doivent être examinés. Nous ne certifions pas encore une validation historique strictement conforme aux informations réellement accessibles à chaque rentrée.

## 6. Les utilisateurs et leurs décisions

Les utilisateurs visés sont les services éducatifs nationaux et territoriaux et les partenaires intervenant dans l'éducation. Ce sont des utilisateurs cibles, pas des utilisateurs dont l'adoption a déjà été évaluée.

Un usage raisonnable consiste à :

1. repérer un territoire au risque estimé élevé ;
2. examiner les facteurs associés et l'incertitude ;
3. confronter le résultat aux informations locales ;
4. choisir une intervention et prévoir son suivi.

Le simulateur de ciblage utilise une efficacité supposée par l'utilisateur. Les « abandons évités » qu'il affiche sont un scénario calculé, pas un effet causal démontré ni un résultat déjà obtenu.

## 7. Ce qui est effectivement livré

- Une application Streamlit avec huit écrans : carte d'alerte, région, province, compréhension de l'abandon, ciblage des actions, fiabilité, perspective et données/méthode.
- Des données de travail et des résultats organisés selon les cinq étapes du challenge.
- Un atlas national et 17 fiches régionales.
- Des scripts, dépendances et commandes pour reproduire les traitements.
- Une documentation finale limitée à 15 pages, accompagnée de documents techniques.

L'application est le livrable final intégrateur : elle s'appuie sur les productions des étapes précédentes. Les fichiers intermédiaires constituent les preuves et la traçabilité de cette solution.

## 8. Questions probables et réponses courtes

**Pourquoi travailler par province alors que le défi parle de régions ?**

Les calculs provinciaux conservent davantage de détail. Nous les restituons ensuite au niveau régional. L'information provinciale ne doit toutefois pas être plus précise que ne le permettent les données d'origine.

**Pourquoi le primaire seulement pour la prévision finale ?**

La chaîne retenue reconstruit et contrôle les flux du primaire et dispose des effectifs permettant les calculs. Les autres niveaux sont analysés, mais le projet ne présente pas de modèle prédictif final suffisamment établi pour eux. La fiche Analyse détaillera les essais et leur validation.

**Votre carte permet-elle de savoir quel élève va abandonner ?**

Non. Elle présente un taux estimé pour un territoire. Un taux provincial ne se transforme pas en diagnostic individuel.

**Un territoire rouge aura-t-il nécessairement beaucoup d'abandons en nombre ?**

Un taux élevé et un grand nombre d'élèves concernés sont deux notions différentes. Le nombre estimé dépend aussi des effectifs. Les deux doivent être examinés.

**Avez-vous démontré que la pauvreté ou les violences causent les abandons ?**

Le modèle exploite des associations statistiques. Les contributions SHAP expliquent le calcul de la prévision ; elles ne démontrent pas, à elles seules, une causalité.

**Les recommandations ont-elles déjà fait leurs preuves ?**

Le projet propose des pistes à discuter avec le terrain. Il n'évalue pas expérimentalement leur efficacité.

**Peut-on annoncer une « précision de 86,1 % » parce que le gain est de 13,9 % ?**

Non. Le bilan actuel indique une réduction relative de l'erreur moyenne par rapport à la reconduction, pas une précision de classification. Les métriques seront expliquées dans la fiche Analyse.

## 9. Ce qui reste à établir

- Justifier la date de disponibilité de chaque famille de variables et les limites de la validation historique.
- Expliquer les calculs géographiques et leurs incertitudes.
- Vérifier la cohérence de toutes les formulations du rapport et de l'application avec la cible et le calendrier décrits ici.
- Documenter les différences entre les anciennes sorties et la dernière exécution, sans attribuer une cause non isolée à un changement de version logicielle.
- Faire valider les pistes d'action et les hypothèses du simulateur par les personnes connaissant le terrain.

## 10. Pièces utilisées pour cette fiche

Chemins relatifs à la racine du projet :

| Pièce | Usage dans le cadrage |
|---|---|
| `documents/Document_du_challenge_Data_Challenge_Burkina.pdf`, pages 2, 4 à 6 | Défi, étapes et livrables attendus ; document relu lors du cadrage des dépôts |
| `livrables/app/pipeline/t07_indicateurs.py` | Définition des indicateurs et classes couvertes |
| `livrables/app/pipeline/t08_facteurs.py` | Calendrier des variables et unité de la table d'analyse |
| `livrables/app/pipeline/t09_modele.py` | Cible principale et protocole de validation |
| `livrables/app/app.py` | Écrans, avertissements et scénario d'intervention |
| `livrables/04_analyse/*bilan-modele_v1.json` | Gain actuel de 13,9 % et limites des résultats |

Les explications ci-dessus décrivent l'implémentation examinée. Les points restant à contrôler sont explicitement distingués des constats vérifiés.
