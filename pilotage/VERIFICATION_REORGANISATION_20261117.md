# Vérification après réorganisation — 17 novembre 2026

Branche : `correction-reorganisation-chemins-depots`.

## Corrections

- Racine commune du projet corrigée dans `livrables/app/pipeline/utils.py` ; sources dans `donnees/`, sorties dans `livrables/`.
- Lectures des étapes 01 à 05, chemins des données de l'application, contrôles d'environnement et de sorties du lanceur corrigés.
- Scripts autonomes d'extraction adaptés aux nouveaux emplacements ; imports relatifs entre leurs fichiers conservés.
- Générateurs de documentation et de LISEZ-MOI adaptés ; LISEZ-MOI général désormais écrit dans `LISEZ-MOI.txt`.
- Commandes de lancement corrigées dans les notices et fichiers de dépendances.
- Archive des sources externes de l'étape 01 conservée ; 23 fichiers vérifiés lors de sa création.

## Exécution et contrôles

Commande exécutée depuis la racine :

```powershell
& .\livrables\app\.app_env\Scripts\python.exe -X utf8 livrables/app/relancer.py
```

Les 12 étapes (t02 à t16) ont terminé avec un code de sortie nul. Tous les contrôles de sorties du lanceur passent, dont les 17 fiches régionales PDF et l'atlas national.

Les huit écrans de l'application ont été exécutés avec les vraies données en mode Streamlit sans serveur : carte, région, province, compréhension de l'abandon, actions, fiabilité, perspective et données/méthode. Aucun appel à `st.error` ni exception d'exécution n'a été observé pour les sélections initiales.

Le test AppTest avec serveur n'a pas pu démarrer : création de la boucle asyncio bloquée dans `socket.socketpair()` (accept sur socket locale). Le fonctionnement HTTP et les interactions dans un navigateur restent à vérifier sur le poste utilisateur. Ce blocage appartient à l'environnement de test ; il ne permet pas de conclure sur le serveur.

## Comparaison avec les résultats enregistrés dans Git

- 31 fichiers CSV/JSON ont été comparés à HEAD dans l'ancienne arborescence, en normalisant les fins de ligne : 16 identiques octet pour octet après normalisation, 15 différents.
- Les CSV des étapes 01 à 03 sont identiques au sens des valeurs numériques (tolérance relative 1e-8 et absolue 1e-10), sans modification du calcul métier.
- Le modèle et ses restitutions présentent des différences réelles : MAE du gradient boosting de 8,178843 à 8,207386 points ; écart maximal des prévisions provinciales de 2,229513 points ; 2 niveaux d'alerte différents.
- Contrôle de régression : le code t09 antérieur à la réorganisation a été exécuté avec `--racine <projet>/livrables` et une sortie temporaire, dans le même environnement que le code corrigé. Toutes ses sorties sont exactement identiques à celles du code corrigé. Les modifications de chemins ne causent donc pas ces différences du modèle.
- L'environnement diffère de celui consigné dans `requirements-versions-testees.txt` : Python 3.12.10, pandas 3.1.1 et numpy 2.5.5 actuellement, contre Python 3.13, pandas 3.0.5 et numpy 2.5.3 consignés. Cette différence est une piste d'explication ; son effet causal exact n'a pas été isolé.
- Les versions effectives de cette exécution figurent dans `livrables/app/requirements-versions-locales.txt`. L'ancien relevé de versions est conservé.

## Limites avant dépôt

La génération PDF a été remplacée par un moteur Python ReportLab (`pdf_documents.py`), à partir du contenu des documents Word. Les quatre rapports PDF sont régénérés sans LibreOffice. Les tableaux, figures, accents, listes, pagination et pieds de page sont pris en charge pour les rapports du projet. Ce moteur n'est pas un convertisseur Word généraliste.

L'extraction des nouveaux PDF passe par PyMuPDF (mode layout), ajouté à `requirements.txt` ; Poppler n'est plus nécessaire. Les extractions historiques mises en cache restent utilisées si leur MD5 est valide, pour conserver les résultats de préparation déjà vérifiés. Une extraction sur PDF neuf et sa relecture via le cache ont été testées avec succès.

Installation des bibliothèques : `python -m pip install -r livrables/app/requirements.txt`. Aucun traitement du projet ne requiert désormais LibreOffice ou Poppler. Le contrôle d'environnement a été adapté. La limite de 15 pages est contrôlée automatiquement lors de la production de la documentation finale.

La chaîne réutilise les huit CSV d'extraction conservés dans `livrables/02_nettoyage/extractions_sources_20261116/` ; elle ne réexécute pas les six scripts d'extraction initiaux. La régénération intégrale de ces extractions à partir des publications n'est pas couverte par ce test.

Ne pas préparer `depot_plateforme/` tant que les écarts du modèle n'ont pas été acceptés ou résolus, le serveur testé sur le poste utilisateur. Les quatre PDF ont été actualisés avec le moteur Python.

Aucun commit ni dépôt sur la plateforme n'a été effectué.

## Validation du remplacement des outils externes

- t15a à t16 relancés avec succès ; contrôle de toutes les sorties réussi.
- Quatre PDF régénérés et inspectés visuellement : schéma 2 pages, parcours 1 page, fiabilité 2 pages, documentation finale 7 pages (maximum 15).
- Le premier rendu de fiabilité laissait une puce isolée en troisième page ; l'interligne a été ajusté et le rendu final vérifié.
- Extraction PyMuPDF sur un PDF neuf de deux pages, séparateurs de pages et relecture du cache testés.
- La dernière relance globale a atteint t14, puis rencontré un PermissionError sur la fiche Nakambé existante. Une seconde tentative a confirmé le verrou. Aucune fermeture forcée de lecteur ni suppression du fichier n'a été tentée. Les rapports t15 ont été relancés indépendamment avec succès.
- Les versions effectives sont consignées ; l'installation dans un environnement vierge n'a pas été testée ici, car l'accès à PyPI est indisponible. Les essais ont utilisé les bibliothèques déjà présentes sur le poste.
- Pour contourner ce verrou sans toucher au fichier ouvert, t14 a ete teste dans un dossier temporaire : 17 fiches PDF d'une page, atlas et synthese generes avec succes.
