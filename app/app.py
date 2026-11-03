"""A small visit counter: just enough app to prove the whole infrastructure works."""
import os
import socket

import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)


def db_password():
    """Reads the password from a Docker secret file if one is given, else from the environment."""
    path = os.environ.get("DB_PASSWORD_FILE")
    if path:
        with open(path, encoding="utf-8") as secret:
            return secret.read().strip()
    return os.environ["DB_PASSWORD"]


def connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ.get("DB_NAME", "appdb"),
        user=os.environ.get("DB_USER", "app"),
        password=db_password(),
        connect_timeout=2,
    )


@app.get("/")
def index():
    """Counts the visit in the database and says which server answered."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO visits (id, total) VALUES (1, 1) "
            "ON CONFLICT (id) DO UPDATE SET total = visits.total + 1 "
            "RETURNING total"
        )
        total = cur.fetchone()[0]
    return jsonify(served_by=socket.gethostname(), visits=total)


@app.get("/healthz")
def healthz():
    """Returns 200 only if this server can really reach the database."""
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
    except psycopg2.OperationalError:
        return jsonify(status="database unreachable"), 503
    return jsonify(status="ok")
