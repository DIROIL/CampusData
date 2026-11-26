"""Tests du dépôt et du traitement des fichiers.

Chaque test suit le même schéma : préparer → agir → vérifier.
"""
from datetime import datetime, timezone

from conftest import upload

from app.worker import run_once

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)  # heure fixe : le test ne dépend pas du jour


# 1 - Créer un jeu : 201, nom sans espaces, owner par défaut, 0 mesure.
def test_create_dataset(client):
    response = client.post("/api/datasets", json={"name": "  Bâtiment A  "})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Bâtiment A"  # espaces externes retirés
    assert body["owner"] == "Équipe"  # absent → valeur par défaut
    assert body["measurement_count"] == 0


# 2 - Nom invalide (422) ou déjà utilisé (409).
def test_name_errors(client):
    assert client.post("/api/datasets", json={"name": "ab"}).status_code == 422  # trop court
    assert client.post("/api/datasets", json={"name": "Jeu", "id": "x"}).status_code == 422  # champ inconnu
    client.post("/api/datasets", json={"name": "Jeu A"})
    assert client.post("/api/datasets", json={"name": "Jeu A"}).status_code == 409  # contrainte UNIQUE


# 3 - Dépôt du fichier de référence : 202 = reçu, pas encore traité.
def test_upload_is_pending(client, dataset_id):
    response = upload(client, dataset_id, "mesures-salles-2026-10-05.csv")
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert "content" not in response.json()  # le fichier brut n'est jamais renvoyé
    assert response.headers["Location"].startswith("/api/ingestions/")


# 4 - Refus par l'API, avant toute création de dépôt : vide 422, type 415, taille 413.
def test_upload_refused(client, dataset_id):
    url = f"/api/datasets/{dataset_id}/ingestions?filename=a.csv"
    assert client.post(url, content=b"", headers={"Content-Type": "text/csv"}).status_code == 422
    assert client.post(url, json={}).status_code == 415  # json= envoie application/json
    big = b"x" * 1_048_577  # 1 Mio + 1 octet
    assert client.post(url, content=big, headers={"Content-Type": "text/csv"}).status_code == 413


# 5 - Traitement du fichier de référence : 63 / 0 / 0.
def test_reference_file(client, dataset_id):
    # Préparer : déposer le fichier.
    ingestion_id = upload(client, dataset_id, "mesures-salles-2026-10-05.csv").json()["id"]
    # Agir : lancer le worker dans le test, avec l'heure fixe NOW.
    run_once(NOW)
    # Vérifier : relire le dépôt et le jeu.
    body = client.get(f"/api/ingestions/{ingestion_id}").json()
    assert body["status"] == "succeeded"
    assert (body["rows_accepted"], body["rows_rejected"], body["rows_duplicate"]) == (63, 0, 0)
    assert client.get(f"/api/datasets/{dataset_id}").json()["measurement_count"] == 63


# 6 - Fichier d'erreurs : 4 / 7 / 1 ET la raison de chaque ligne rejetée.
def test_error_file(client, dataset_id):
    ingestion_id = upload(client, dataset_id, "mesures-avec-erreurs.csv").json()["id"]
    run_once(NOW)
    body = client.get(f"/api/ingestions/{ingestion_id}").json()
    # La ligne 11 répète la ligne 3 : valide, mais comptée en doublon.
    assert (body["rows_accepted"], body["rows_rejected"], body["rows_duplicate"]) == (4, 7, 1)
    assert body["errors"] == [
        {"line": 5, "reason": "Invalid co2_ppm"},
        {"line": 6, "reason": "Invalid humidity_pct"},
        {"line": 7, "reason": "Invalid measured_at"},
        {"line": 8, "reason": "Invalid room"},
        {"line": 9, "reason": "measured_at in the future"},
        {"line": 10, "reason": "Invalid temperature_c"},
        {"line": 12, "reason": "Expected 5 columns"},
    ]


# 7 - Idempotence : un second dépôt du même fichier n'ajoute aucune mesure.
def test_second_upload_adds_nothing(client, dataset_id):
    upload(client, dataset_id, "mesures-salles-2026-10-05.csv")
    run_once(NOW)
    second = upload(client, dataset_id, "mesures-salles-2026-10-05.csv").json()["id"]
    run_once(NOW)
    body = client.get(f"/api/ingestions/{second}").json()
    # ON CONFLICT DO NOTHING : les 63 lignes existent déjà → 0 insérée, 63 doublons.
    assert (body["rows_accepted"], body["rows_duplicate"]) == (0, 63)
    assert client.get(f"/api/datasets/{dataset_id}").json()["measurement_count"] == 63


# 8 et 9 - En-tête invalide → failed sans aucune mesure ; relance 200 puis 409.
def test_invalid_header_and_retry(client, dataset_id):
    ingestion_id = upload(client, dataset_id, "en-tete-invalide.csv").json()["id"]
    run_once(NOW)
    body = client.get(f"/api/ingestions/{ingestion_id}").json()
    assert (body["status"], body["error_message"]) == ("failed", "Invalid header")
    assert client.get(f"/api/datasets/{dataset_id}").json()["measurement_count"] == 0  # ROLLBACK total
    # 1re relance : le dépôt est failed → 200, il repasse en pending.
    assert client.post(f"/api/ingestions/{ingestion_id}/retry").status_code == 200
    # 2e relance : il est maintenant pending, plus failed → 409.
    assert client.post(f"/api/ingestions/{ingestion_id}/retry").status_code == 409


# 10 - Indicateurs : valeurs de A101 ; période inversée → 422.
def test_stats(client, dataset_id):
    upload(client, dataset_id, "mesures-salles-2026-10-05.csv")
    run_once(NOW)
    rooms = client.get(f"/api/datasets/{dataset_id}/stats").json()["rooms"]
    assert [r["room"] for r in rooms] == ["A101", "A102", "B201"]  # triées par salle
    a101 = rooms[0]
    assert (a101["measurements"], a101["co2_avg"], a101["co2_min"], a101["co2_max"]) == (21, 636.1, 430, 1092)
    assert (a101["temperature_avg"], a101["humidity_avg"]) == (20.3, 44.2)
    bad = client.get(f"/api/datasets/{dataset_id}/stats?from=2026-10-06T00:00:00Z&to=2026-10-05T00:00:00Z")
    assert bad.status_code == 422


# 11 - Suppression : 204 sans contenu, puis le jeu n'existe plus (404).
def test_delete_dataset(client, dataset_id):
    upload(client, dataset_id, "mesures-salles-2026-10-05.csv")
    run_once(NOW)
    response = client.delete(f"/api/datasets/{dataset_id}")
    assert response.status_code == 204 and response.content == b""
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404


# 12 - Identifiants : UUID valide mais inconnu → 404 ; texte qui n'est pas un UUID → 422.
def test_unknown_and_malformed_ids(client):
    assert client.get("/api/datasets/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/datasets/pas-un-uuid").status_code == 422
