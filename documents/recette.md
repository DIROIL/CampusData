# Rapport de recette

**Équipe :** à renseigner (nom du binôme). **Date :** 2026-11-26 (essais en ligne de commande du 2026-11-18 inclus).
**Exécutant/relecteur :** Diroil (exécutant, avec assistance) / relecteur : à renseigner (autre membre du binôme, recette à refaire sans aide, voir §6).
**Commit applicatif :** version S2 non encore commitée au moment de la recette. Base : commit S1 `32a875e`, puis modifications locales de la S2 (`api/`, `web/`, `compose.dev.yaml`). À remplacer par le hash du commit S2.
**Digests API/web :** non applicable : aucune image construite en S2, l'API tourne sur le poste.
**Contexte de déploiement et commit de configuration :** développement local S1-S2 (`compose.dev.yaml` : PostgreSQL, Nginx et Kafka en conteneurs, API et worker sur le poste).

## 1. Conditions d’exécution

- **Poste :** MacBook Air, macOS (Darwin 25.6), shell zsh, Docker Desktop.
- **Versions utiles :** Python 3.12 (`.venv`), dépendances figées dans `api/requirements-dev.lock` (FastAPI 0.163.1, SQLAlchemy 2.0.57, psycopg 3.3.9, confluent-kafka 2.16.1, pytest 9.2.0, ruff 0.17.5), PostgreSQL 17 (`postgres:17-alpine`), Nginx (`nginx-unprivileged:stable-alpine`), Kafka 4.1.0 (`apache/kafka:4.1.0`, mode KRaft).
- **Terminaux :**
  - T1 : API Uvicorn, port 8000, base `campus` ;
  - T2 : curl, worker `--once` et simulateur, base `campus` ;
  - T3 : pytest, base `campus_test` ;
  - T4 : consommateur Kafka `app.stream`, base `campus`.
- **Bases dédiées :** `campus` pour les essais manuels et l'interface, `campus_test` pour les tests automatiques. L'URL de connexion est construite depuis `.env`, qui n'est pas versionné. Aucun mot de passe ni DSN complet n'apparaît dans ce rapport.
- **Données de départ :** fichiers du kit `data/mesures-salles-2026-10-05.csv` (référence, 63 lignes), `data/mesures-avec-erreurs.csv`, `data/en-tete-invalide.csv`. Pour Kafka : `app.simulator`.
- **Préconditions :** tables créées par `python -m app.init_db` dans chaque base. Interface servie par Nginx sur `http://127.0.0.1:8080`, qui relaie `/api/` vers l'API du poste.
- **Nettoyage des tests d'intégration :**
  - `api/tests/conftest.py` vide la base avant **chaque** test (`TRUNCATE datasets CASCADE`) ;
  - protection : un `assert` refuse de démarrer si `DATABASE_URL` ne se termine pas par `_test`. Ce contrôle est placé avant l'import de l'application, donc la base `campus` ne peut pas être vidée par erreur ;
  - le worker est lancé dans les tests avec une heure fixe (`NOW = 2026-11-16 UTC`), pour que le résultat ne dépende pas du jour d'exécution.
- **Limite :** la base `campus` contenait déjà des jeux créés lors des essais curl de la tâche 4 (« Essai … », « Bâtiment A » avec un dépôt `deuxieme.csv`). Certains compteurs observés dans l'interface en tiennent compte (voir US07 et US08).

## 2. Résultats par exigence

Référentiel : user stories et critères d'acceptation de `S1/task2.md`.

| ID du référentiel | **Préconditions** | Action / commande | Attendu | Observé | Preuve | Résultat |
|---|---|---|---|---|---|---|
| US01 positif | Aucun jeu du même nom | Interface : créer un jeu | 201, jeu listé avec 0 mesure | `POST /api/datasets 201 Created`, le jeu apparaît dans la liste. Nom `<b>A</b>` affiché comme du texte, sans gras | Log Uvicorn T1 ; test `test_create_dataset` | validé |
| US01 erreur | Jeu existant | Interface : recréer le même nom | 409, un seul jeu de ce nom | `POST /api/datasets 409 Conflict` ; message « Erreur 409 : Dataset name already exists » | Log Uvicorn T1 ; test `test_name_errors` | validé |
| US02 positif | Jeu contenant des mesures | Interface : afficher la liste, ouvrir le jeu | Jeu listé avec son nombre de mesures, ouverture 200 | Liste « Nom (N mesures) » ; `GET …/ingestions 200` et `GET …/stats 200` à l'ouverture | Log Uvicorn T1 | validé |
| US02 erreur | UUID inconnu / texte non UUID | `GET /api/datasets/0000…0000` et `/api/datasets/pas-un-uuid` | 404 / 422 | 404 et 422 (assertions vertes) | `test_unknown_and_malformed_ids` (pytest) | validé |
| US03 positif | Jeu de test `<b>A</b>` | Interface : Supprimer puis OK | 204 sans corps, jeu retiré | Message « Jeu « <b>A</b> » supprimé. », jeu retiré de la liste. Requête DELETE 204 visible dans l'onglet Network de Chrome. 404 à la relecture vérifié par pytest | Onglet Network Chrome ; `test_delete_dataset` | validé |
| US03 erreur | Fenêtre de confirmation ouverte | Interface : Supprimer puis Annuler | Aucune requête, jeu conservé | Aucune requête DELETE dans l'onglet Network, jeu toujours listé | Onglet Network Chrome | validé |
| US04 positif | Jeu existant | Interface : déposer `mesures-salles-2026-10-05.csv` | 202, dépôt pending | `POST …/ingestions?filename=mesures-salles-2026-10-05.csv 202 Accepted` ; page « Statut : pending » | Log Uvicorn T1 (dépôt `cb10b5b5…`) | validé |
| US04 erreur | Jeu existant | Dépôt vide / JSON / plus de 1 Mio | 422 / 415 / 413, aucun dépôt | 422 / 415 / 413 (assertions vertes) | `test_upload_refused` (pytest) | validé |
| US05 positif | Dépôt pending du fichier de référence, dans un jeu neuf | `python -m app.worker --once`, puis lecture dans l'interface | succeeded, 63 acceptées | Jeu « Bâtiment A » : `mesures-salles-2026-10-05.csv succeeded 63 0 0` | Copie de l'écran Dépôts ; `test_reference_file` | validé |
| US05 erreur | Dépôt de `en-tete-invalide.csv` | Worker `--once` | failed « Invalid header », 0 mesure insérée | Worker : `dépôt 82f4568a… : failed (Invalid header)` ; page « Statut : failed - Invalid header ». Rapport : « Fichier refusé : Invalid header / Aucune ligne rejetée ». 0 mesure vérifié par pytest | Log worker T2 ; `test_invalid_header_and_retry` | validé |
| US06 positif | Dépôt de `mesures-avec-erreurs.csv` | Worker `--once`, puis bouton Rapport | succeeded 4 / 7 / 1, une raison par ligne rejetée | `succeeded 4 7 1`. Rapport de 7 lignes : 5 Invalid co2_ppm, 6 Invalid humidity_pct, 7 Invalid measured_at, 8 Invalid room, 9 measured_at in the future, 10 Invalid temperature_c, 12 Expected 5 columns | Log worker `0952c1e2… succeeded (4 acceptées)` ; `test_error_file` | validé |
| US06 erreur | Ligne avec une température non numérique | Même dépôt | Ligne rejetée, dépôt non failed | Ligne 10 rejetée « Invalid temperature_c » ; le dépôt reste succeeded et les lignes suivantes sont traitées | `test_error_file` ; Rapport dans l'interface | validé |
| US07 positif | Jeu contenant déjà les 63 mesures de référence | Redéposer le même fichier, puis lancer le worker | succeeded, 0 acceptée, 63 doublons, toujours 63 mesures | Interface : `deuxieme.csv succeeded 0 0 63`. Dans le jeu « Essai … », le worker affiche `succeeded (0 acceptées)`. `measurement_count` = 63 à la relecture : vérifié par pytest | Log worker `cb10b5b5…` ; `test_second_upload_adds_nothing` | validé |
| US07 erreur | Fichier contenant deux fois la même salle à la même heure | Traitement de `mesures-avec-erreurs.csv` (ligne 11 = ligne 3) | Seconde ligne comptée en doublon | 1 doublon compté, non inséré | `test_error_file` ; écran Dépôts | validé |
| US08 positif | Les 63 mesures de référence seules | `curl …/stats?room=A101` | A101 : 21 mesures, CO₂ 636.1 / 430 / 1092, température 20.3, humidité 44.2 | `{"measurements":21,"co2_avg":636.1,"co2_min":430,"co2_max":1092}` ; 3 salles A101, A102, B201 ; température et humidité vérifiées par pytest | Sortie curl T2 (2026-11-18) ; `test_stats` | validé |
| US08 positif (interface) | Jeu « Bâtiment A » : référence + 4 mesures acceptées du fichier d'erreurs | Interface : salle A101, Filtrer | Une ligne A101 | `A101 23 627.2 430 1092 20.3 44.2`, dernière mesure 06/10/2026 08:30. Écart attendu : 2 mesures A101 du 06/10 viennent du fichier d'erreurs | Copie de l'écran Indicateurs | validé |
| US08 erreur | Jeu ouvert | Du = 06/10/2026 00:00, Au = 05/10/2026 00:00, Filtrer ; et `curl …/stats?from=…06…&to=…05…` | 422 et message lisible | Interface : « Erreur 422 : from must be before to » ; curl : `période inversée : 422` | Écran ; sortie curl T2 | validé |
| US09 positif | Dépôt `en-tete-invalide.csv` failed | Interface : Relancer, puis worker `--once` | pending, puis nouveau traitement | Message « relancé », statut pending. Le worker retraite le même dépôt `82f4568a…`, qui redevient `failed (Invalid header)` : normal, le fichier n'a pas changé | Log worker T2 (deux passages du même ID) | validé |
| US09 erreur | Dépôt succeeded | `curl -X POST …/ingestions/{id}/retry` | 409, statut inchangé | `relance d un dépôt succeeded : 409` ; relance d'un dépôt pending : 409 (pytest) | Sortie curl T2 ; `test_invalid_header_and_retry` | validé |
| US10 positif | Jeu de 63 mesures | Redémarrer les conteneurs sans supprimer le volume | Jeu toujours présent avec 63 mesures | Non exécuté en S2 | - | non exécuté (prévu en S3) |
| US10 erreur | PostgreSQL arrêté | `GET /health/ready` et `/health/live` | 503 / 200 | Non exécuté | - | non exécuté (prévu en S3) |
| Interface : panne API | API arrêtée (Ctrl+C dans T1), Nginx actif | Interface : Créer | Message d'erreur, bouton réactivé | « Erreur 502 : Bad Gateway », bouton Créer de nouveau cliquable | Écran | validé |
| S2 tâche 5b : flux Kafka | Kafka démarré, consommateur `app.stream` lancé | `python -m app.simulator --count 30 --interval 1` sur un flux neuf | 30 / 24 / 3 / 3 ; raisons Invalid co2_ppm, Invalid message, Invalid humidity_pct | Deux envois cumulés, le jeu du flux n'ayant pas été supprimé entre les deux : `rows_total 60, accepted 48, rejected 6, duplicate 6`. Raisons : les 3 attendues, chacune deux fois. Cohérent avec 2 × 30/24/3/3, mais le flux neuf n'a pas été observé | Logs T2 (simulateur) et T4 (consommateur) ; `curl …/ingestions` du jeu « Flux capteurs (Kafka) » | non exécuté (flux neuf) |
| Qualité : lint | Code S2 complet | `python -m ruff check api` | All checks passed! | `All checks passed!` (2026-11-26, après l'ajout de Kafka) | Sortie terminal | validé |
| Qualité : tests | Base `campus_test` | `python -m pytest -q` | Tous verts | `13 passed`. Lancé **avant** l'ajout de `stream.py`, de `simulator.py` et de la nouvelle interface | Sortie T3 | à relancer (voir A1) |

## 3. Cas détaillé : idempotence du second dépôt (US07)

- **Précondition :** jeu de données contenant déjà les 63 mesures de `data/mesures-salles-2026-10-05.csv`.
- **Action :** redéposer le même fichier (dépôt `deuxieme.csv` dans « Bâtiment A », dépôt `cb10b5b5…` dans « Essai … »), puis `python -m app.worker --once`.
- **Attendu :** dépôt `succeeded` avec 0 acceptée et 63 doublons ; `measurement_count` toujours égal à 63 à la relecture.
- **Observé :**
  - worker : `dépôt cb10b5b5… : succeeded (0 acceptées)` ;
  - interface : `deuxieme.csv succeeded 0 0 63` ;
  - test automatique `test_second_upload_adds_nothing` vert : 0 acceptée, 63 doublons et `measurement_count == 63` à la relecture.
- **Preuve :** log du worker (T2), écran Dépôts, sortie pytest.
- **Conclusion :** validé. Le comptage des doublons repose sur `INSERT … ON CONFLICT DO NOTHING RETURNING` et la contrainte `uq_measurement`, pas sur le seul statut `succeeded`.

## 4. Expériences de déploiement et de reprise

Aucune de ces expériences n'est exécutée en S2 : la conteneurisation de l'API commence en S3.

| Expérience | Résultat |
|---|---|
| Persistance Compose | non exécuté (S3) |
| Réconciliation API | non exécuté (S4) |
| Panne DB (liveness, readiness) | non exécuté (S3 et S4) |
| Cloud | non exécuté |
| Rollback | non exécuté |
| Restauration | non exécuté |

## 5. Anomalies connues

| ID | Reproduction minimale | Attendu/observé | Impact | Priorité | Correction ou contournement | État |
|---|---|---|---|---|---|---|
| A1 | `pytest -q` lancé avant l'ajout de Kafka (`stream.py`, `simulator.py`, `confluent-kafka`) et avant la refonte de l'interface | Tests verts attendus sur la version commitée ; dernier résultat observé sur une version antérieure | Technique : preuve non rattachée à la version finale | Haute : bloque le commit S2 | Relancer `ruff` et `pytest -q` dans T3 juste avant le commit, et noter le hash | Ouvert |
| A2 | Interface passée à deux écrans (liste / détail, avec animation), styles des maquettes S1 | Parcours 1 à 12 validé sur la version « solution du cours » ; pas rejoué sur la nouvelle mise en page | Utilisateur : régression possible non détectée | Haute | Rejouer le parcours complet (création, 409, dépôt, worker, Rapport, Relancer, filtre A101, 422, Supprimer/Annuler/OK, API arrêtée) sur la nouvelle interface | Ouvert |
| A3 | Flux Kafka : simulateur lancé deux fois sans suppression du jeu du flux | Attendu 30/24/3/3 sur un flux neuf ; observé 60/48/6/6 (cumul) | Preuve incomplète, fonctionnement cohérent | Moyenne | Supprimer le jeu « Flux capteurs (Kafka) » (DELETE 204), renvoyer 30 messages, relever les compteurs | Ouvert |
| A4 | Interface, colonne Statut des dépôts | Maquette : pastille verte ou rouge selon le statut ; observé : pastille neutre et statut écrit en toutes lettres | Cosmétique : l'information reste lisible | Basse | Ajouter une classe CSS selon le statut dans `loadIngestions` | Ouvert |
| A5 | `S1/task2.md`, critère US06 (« ligne 5 : CO2 négatif ») | Raison réellement renvoyée par l'API : `Invalid co2_ppm` (contrat) | Documentaire | Basse | Aligner l'exemple du critère sur le libellé du contrat | Ouvert |
| A6 | Interface : la liste des jeux est une liste, pas le tableau de la maquette (pas de colonnes Responsable ni Créé le, pas de champ Description) | Écart avec la maquette S1 | Utilisateur : informations absentes de l'écran | Basse | Étendre `renderDatasets` et le formulaire | Ouvert |

## 6. Synthèse de remise

- **Critères validés (S2) :**
  - US01 à US09, positifs et erreurs ;
  - comportement de l'interface quand l'API est arrêtée ;
  - lint `ruff`.
- **Écarts restants :**
  - A1 : relancer pytest sur la version finale ;
  - A2 : rejouer le parcours sur la nouvelle interface ;
  - A3 : preuve du flux Kafka neuf ;
  - A4 à A6 : écarts cosmétiques ou documentaires.
- **Non exécuté :** US10 (persistance et panne DB) et toutes les expériences du §4, prévues à partir de la S3.
- **Limites :**
  - recette faite par l'exécutant avec assistance. La consigne demande que **l'autre membre du binôme** rejoue le parcours **sans aide** : à faire et à consigner ici (relecteur, date, résultat) ;
  - les preuves sont pour l'instant des sorties de terminal et des copies d'écran **non archivées**. Elles sont à enregistrer dans `proofs/` (`proofs/s2-interface.txt`, `proofs/s2-worker.txt`, `proofs/s2-kafka.txt`, `proofs/s2-pytest.txt`), sans secret.
- **Version à évaluer :** le commit S2 (`feat: API, worker, flux Kafka, interface et tests`), une fois A1 et A2 levées. Son hash est à reporter en tête de ce document.

## Comment annoter une preuve

Donnez un nom explicite à chaque sortie conservée : séance, scénario et version.
Convention commune du support : `proofs/sN-sujet.ext`, par exemple
`proofs/s3-persistance.txt`, `proofs/s4-reconciliation.txt`,
`proofs/s6-overlay-s5.yaml` ou `proofs/latence-k3d.json`. Les fichiers privés
(dump, sorties non expurgées) vont uniquement dans `proofs/private/`, ignoré par Git.
Ajoutez une phrase qui indique ce que le lecteur doit observer. Exemple de forme :
« Sur la réponse de relecture, comparer l’identifiant du jeu, son nombre de mesures et sa somme de contrôle à ceux relevés avant
la recréation. » Complétez ensuite avec vos valeurs et votre **résultat réel**.

N’utilisez pas un exemple du cours comme **résultat observé**. Expurgez les secrets,
mais conservez les statuts, identifiants de jeux de données fictifs et messages utiles
pour comprendre le scénario.
