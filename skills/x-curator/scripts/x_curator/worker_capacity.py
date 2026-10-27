"""Ordinary and explicitly approved work share the same two source-worker slots."""

def available(db, now):
    return db.execute("SELECT count(*) FROM jobs WHERE state='leased' AND lease_until>?", (now,)).fetchone()[0] < 2
