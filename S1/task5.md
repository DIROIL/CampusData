# Tâche 5 - Contrat HTTP

Routes reprises du plan de `web/app.js` du starter. Noms de champs et codes à comparer avec la page « contrat HTTP » du cours.

Format des erreurs : `{"detail": "message lisible"}` (format par défaut de FastAPI).

## Les routes

| Méthode | Chemin | Entrée | Succès | Erreurs possibles |
|---|---|---|---|---|
| GET | `/health/live` | — | 200 `{"status":"ok"}` | — |
| GET | `/health/ready` | — | 200 `{"status":"ready"}` | 503 base indisponible |
| GET | `/api/version` | — | 200 `{"version":"dev"}` | — |
| GET | `/api/datasets` | — | 200 liste des jeux | 503 |
| POST | `/api/datasets` | JSON `name`, `description`, `owner` | 201 jeu créé | 409 nom déjà utilisé, 422 nom vide |
| GET | `/api/datasets/{id}` | — | 200 le jeu | 404 inconnu |
| DELETE | `/api/datasets/{id}` | — | 204 sans corps | 404 inconnu |
| POST | `/api/datasets/{id}/ingestions?filename=…` | fichier CSV brut, `Content-Type: text/csv` | 202 dépôt `pending` | 404 jeu inconnu, 413 > 1 Mio, 415 pas un CSV, 422 fichier vide |
| GET | `/api/datasets/{id}/ingestions?status=…` | filtre optionnel | 200 liste des dépôts | 404 jeu inconnu |
| GET | `/api/ingestions/{id}` | — | 200 dépôt + compteurs + erreurs | 404 inconnu |
| POST | `/api/ingestions/{id}/retry` | — | 202 retour en `pending` | 404 inconnu, 409 pas `failed` |
| GET | `/api/datasets/{id}/stats?room=&from=&to=` | filtres optionnels, dates ISO avec fuseau | 200 indicateurs par salle | 404 jeu inconnu, 422 `from` > `to` |

## Exemple 1 - Créer un jeu → 201

Requête :

```http
POST /api/datasets
Content-Type: application/json

{"name": "Qualité de l'air - bâtiment A", "description": "Capteurs CO₂", "owner": "Diroil"}
```

Réponse :

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "3f2a8c1e-…", "name": "Qualité de l'air - bâtiment A", "description": "Capteurs CO₂",
 "owner": "Diroil", "measurement_count": 0, "created_at": "2026-11-17T10:30:00+01:00"}
```

## Exemple 2 - Déposer un fichier → 202

Requête :

```http
POST /api/datasets/3f2a8c1e-…/ingestions?filename=mesures-salles-2026-10-05.csv
Content-Type: text/csv

room,measured_at,co2_ppm,temperature_c,humidity_pct
A101,2026-10-05T08:00:00+02:00,430,19.5,42.0
…
```

Réponse :

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{"id": "9b7d…", "dataset_id": "3f2a8c1e-…", "filename": "mesures-salles-2026-10-05.csv",
 "status": "pending", "rows_accepted": null, "rows_rejected": null, "rows_duplicate": null}
```

202 signifie « reçu et en attente », pas « traité » : c'est le worker qui traite le dépôt ensuite.

## Exemple 3 - Lire un dépôt traité → 200

Requête :

```http
GET /api/ingestions/9b7d…
```

Réponse :

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id": "9b7d…", "filename": "mesures-avec-erreurs.csv", "status": "succeeded",
 "rows_accepted": 4, "rows_rejected": 7, "rows_duplicate": 1,
 "errors": [{"line": 5, "reason": "co2_ppm hors limites"},
            {"line": 6, "reason": "humidity_pct hors limites"}, …],
 "error_message": null}
```

## Exemple 4 - Relancer un dépôt réussi → 409

Requête :

```http
POST /api/ingestions/9b7d…/retry
```

Réponse :

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{"detail": "Seul un dépôt failed peut être relancé"}
```

## Rappel des codes HTTP

| Code | Sens dans CampusData |
|---|---|
| 200 | lecture réussie |
| 201 | jeu créé |
| 202 | dépôt reçu, pas encore traité |
| 204 | suppression réussie, sans corps |
| 404 | jeu ou dépôt inconnu |
| 409 | conflit : nom déjà pris, ou relance d'un dépôt non `failed` |
| 413 | fichier trop gros (> 1 Mio) |
| 415 | pas un CSV |
| 422 | entrée invalide : nom vide, fichier vide, `from` > `to` |
| 503 | base de données indisponible |
