"""Integration tests against a real PostgreSQL. Skipped when DB_HOST is not set."""
import os

import pytest

import app as visit_counter

pytestmark = pytest.mark.skipif("DB_HOST" not in os.environ, reason="needs a PostgreSQL database")


@pytest.fixture
def client():
    return visit_counter.app.test_client()


def test_healthz_is_ok_with_a_database(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_each_visit_increments_the_shared_counter(client):
    first = client.get("/").get_json()
    second = client.get("/").get_json()

    assert second["visits"] == first["visits"] + 1
    assert first["served_by"]
