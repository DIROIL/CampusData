"""Préparation commune aux tests : base campus_test vidée avant chaque test."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Sécurité : refuser de lancer les tests ailleurs que sur une base *_test.
# Les tests vident les tables : sur la base campus, ils effaceraient vos essais.
# Ce contrôle est placé AVANT d'importer l'application, qui ouvre la connexion.
assert os.environ["DATABASE_URL"].endswith("_test"), "DATABASE_URL doit cibler campus_test"

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402

# Dossier data/ du dépôt : les tests utilisent les vrais fichiers du kit.
DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(autouse=True)
def clean_database():
    # autouse : lancé automatiquement avant CHAQUE test. Chaque test part d'une
    # base vide et ne dépend donc pas du résultat des autres.
    # CASCADE : vider datasets vide aussi ingestions et measurements (clés étrangères).
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE datasets CASCADE"))


@pytest.fixture
def client():
    # TestClient appelle l'API directement dans le processus de test :
    # pas besoin d'Uvicorn, de Nginx ni du réseau.
    return TestClient(app)


@pytest.fixture
def dataset_id(client):
    # Préparer : un jeu vide, prêt à recevoir des dépôts.
    return client.post("/api/datasets", json={"name": "Jeu de test"}).json()["id"]


def upload(client, dataset_id, filename):
    """Déposer un fichier de data/ et renvoyer la réponse."""
    # content= envoie les octets tels quels (comme curl --data-binary).
    return client.post(
        f"/api/datasets/{dataset_id}/ingestions?filename={filename}",
        content=(DATA / filename).read_bytes(),
        headers={"Content-Type": "text/csv"},
    )
