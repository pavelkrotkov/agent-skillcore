"""Private SQLite storage keeps response bytes and checkpoints in one transaction."""
import hashlib
import json
from pathlib import Path
import sqlite3

from .stage_timings import initialize as initialize_stages


def open_store(root):
    root = Path(root).expanduser().resolve()
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("private corpus must be outside every Git checkout")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    path = root / "curator.sqlite3"
    for name in ("curator.sqlite3", "curator.sqlite3-wal", "curator.sqlite3-shm", "curator.sqlite3-journal"):
        if (root / name).is_symlink():
            raise ValueError("SQLite files must not be symlinks")
    db = sqlite3.connect(path, timeout=30)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, account TEXT NOT NULL,
            started REAL NOT NULL, state TEXT NOT NULL, cursor TEXT,
            requests INTEGER NOT NULL DEFAULT 0, reason TEXT
        );
        CREATE TABLE IF NOT EXISTS responses (
            run TEXT NOT NULL REFERENCES collections(id), number INTEGER NOT NULL,
            cursor TEXT, status INTEGER NOT NULL, fetched REAL NOT NULL,
            sha256 TEXT NOT NULL, body BLOB NOT NULL, PRIMARY KEY(run,number)
        );
        CREATE TABLE IF NOT EXISTS selections (
            run TEXT NOT NULL, id TEXT NOT NULL, response INTEGER NOT NULL,
            entry TEXT NOT NULL, availability TEXT NOT NULL,
            PRIMARY KEY(run,id),
            FOREIGN KEY(run,response) REFERENCES responses(run,number)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS selections_id_run ON selections(id,run)")
    initialize_stages(db)
    return db


def sha256(body):
    return hashlib.sha256(body).hexdigest()


def selected_entries(db, run):
    return [json.loads(row[0]) for row in db.execute(
        "SELECT entry FROM selections WHERE run=? ORDER BY response,id", (run,)
    )]


def coverage(db, run):
    row = dict(db.execute("SELECT * FROM collections WHERE id=?", (run,)).fetchone())
    row["selected"] = db.execute("SELECT count(*) FROM selections WHERE run=?", (run,)).fetchone()[0]
    row["unavailable"] = db.execute(
        "SELECT count(*) FROM selections WHERE run=? AND availability='unavailable'", (run,)
    ).fetchone()[0]
    row["historical_complete"] = False
    row["coverage_boundary"] = "Only the timeline currently exposed by X; historical completeness is unproven."
    return row
