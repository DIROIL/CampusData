# Tâche 4 - Décrire les données

Les lignes marquées (à vérifier) sont à comparer avec le modèle de données du cours.

## Table `datasets` (jeux de données)

| Colonne | Type | Obligatoire | Contrainte |
|---|---|---|---|
| id | uuid | oui | PK, générée à la création |
| name | varchar(100) | oui | UNIQUE (sinon 409), non vide |
| description | text | non | — |
| owner | varchar(100) | oui | responsable déclaré, pas un compte (à vérifier) |
| created_at | timestamptz | oui | valeur par défaut : now() |

## Table `ingestions` (dépôts de fichiers)

| Colonne | Type | Obligatoire | Contrainte |
|---|---|---|---|
| id | uuid | oui | PK |
| dataset_id | uuid | oui | FK vers datasets.id, ON DELETE CASCADE (supprimé avec le jeu) |
| filename | varchar(255) | oui | — |
| content | bytea | oui | contenu du CSV, conservé en base en attendant le worker (à vérifier) |
| status | varchar(20) | oui | CHECK parmi pending, running, succeeded, failed ; défaut pending |
| rows_accepted | int | non | ≥ 0, vide tant que le dépôt n'est pas traité |
| rows_rejected | int | non | ≥ 0 |
| rows_duplicate | int | non | ≥ 0 |
| errors | jsonb | non | liste des rejets : numéro de ligne et raison |
| error_message | text | non | rempli seulement si failed (ex. « en-tête invalide ») |
| created_at | timestamptz | oui | défaut now() |
| finished_at | timestamptz | non | rempli quand le dépôt est succeeded ou failed |

## Table `measurements` (mesures)

| Colonne | Type | Obligatoire | Contrainte |
|---|---|---|---|
| id | bigint | oui | PK, numéro généré automatiquement |
| dataset_id | uuid | oui | FK vers datasets.id, ON DELETE CASCADE |
| ingestion_id | uuid | oui | FK vers ingestions.id (le dépôt qui a inséré la mesure) |
| room | varchar(50) | oui | non vide |
| measured_at | timestamptz | oui | avec fuseau horaire, pas dans le futur |
| co2_ppm | int | oui | CHECK entre 0 et 5000 (à vérifier) |
| temperature_c | numeric(4,1) | oui | CHECK entre -20 et 50 (à vérifier) |
| humidity_pct | numeric(4,1) | oui | CHECK entre 0 et 100 |

Contrainte de table : **UNIQUE (dataset_id, room, measured_at)**. C'est elle qui empêche les doublons (US07).

Relations : un jeu **reçoit** plusieurs dépôts ; un jeu **contient** plusieurs mesures ; un dépôt **a inséré** plusieurs mesures.

## Exemples valides et invalides

Exemples invalides tirés de `data/mesures-avec-erreurs.csv`.

| Colonne | Exemple valide | Exemple invalide | Raison du rejet |
|---|---|---|---|
| co2_ppm | 455 | -40 (ligne 5) | une concentration ne peut pas être négative |
| temperature_c | 19.6 | abc (ligne 10) | ce n'est pas un nombre |
| humidity_pct | 43.0 | 140 (ligne 6) | une humidité dépasse au maximum 100 % |

## Les trois cas à distinguer

| Cas | Exemple | Ce qui se passe |
|---|---|---|
| Ligne invalide | co2_ppm = abc | la ligne est rejetée et comptée ; le dépôt continue |
| Fichier invalide | en-tête faux (room;date;co2) | le dépôt passe à failed ; aucune mesure n'est insérée |
| Doublon | même salle, même heure (ligne 11 = ligne 3) | la ligne est ignorée et comptée ; ce n'est pas une erreur |
