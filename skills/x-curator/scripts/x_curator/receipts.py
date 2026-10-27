"""Append-only evidence, model executions and publication versions."""
import json

from .storage import sha256


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(value):
    return sha256(encoded(value))


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS captures (
            id TEXT PRIMARY KEY, token TEXT NOT NULL REFERENCES attempts(token),
            payload TEXT NOT NULL, sha TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY, token TEXT NOT NULL REFERENCES attempts(token),
            role TEXT NOT NULL, model TEXT NOT NULL, input TEXT NOT NULL,
            input_sha TEXT NOT NULL, started REAL NOT NULL, finished REAL,
            session TEXT, output TEXT, output_sha TEXT, log BLOB, log_sha TEXT,
            UNIQUE(token,role)
        );
        CREATE TABLE IF NOT EXISTS publications (
            id TEXT PRIMARY KEY, account TEXT NOT NULL, source TEXT NOT NULL,
            proposal TEXT NOT NULL REFERENCES executions(id),
            review TEXT NOT NULL REFERENCES executions(id),
            path TEXT NOT NULL UNIQUE, body BLOB NOT NULL, sha TEXT NOT NULL,
            state TEXT NOT NULL, created REAL NOT NULL,
            FOREIGN KEY(account,source) REFERENCES jobs(account,id)
        );
        CREATE TABLE IF NOT EXISTS publication_audit_failures (
            id INTEGER PRIMARY KEY, publication TEXT NOT NULL REFERENCES publications(id),
            created REAL NOT NULL, error TEXT NOT NULL
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS captures_token_id ON captures(token,id)")
