"""Unit tests: no database needed, the connection is replaced where required."""
import psycopg2
import pytest

import app as visit_counter


@pytest.fixture
def client():
    return visit_counter.app.test_client()


def test_password_comes_from_the_secret_file(tmp_path, monkeypatch):
    secret = tmp_path / "db_password"
    secret.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret))
    monkeypatch.setenv("DB_PASSWORD", "from-env")

    assert visit_counter.db_password() == "from-file"


def test_password_falls_back_to_the_environment(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "from-env")

    assert visit_counter.db_password() == "from-env"


def test_healthz_reports_503_when_the_database_is_down(client, monkeypatch):
    def unreachable():
        raise psycopg2.OperationalError("connection refused")

    monkeypatch.setattr(visit_counter, "connect", unreachable)

    response = client.get("/healthz")

    assert response.status_code == 503
    assert response.get_json() == {"status": "database unreachable"}
