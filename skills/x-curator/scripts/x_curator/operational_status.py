"""Recorded delivery and graph status never substitutes for a proof audit."""
from .graph_status import exists, organization
from .storage import coverage
from .notification_status import recent, state


def notifications(db):
    counts = dict(prepared=0, observed=0, unobserved=0, recorded_failures=0, last_observed_prepared_at=None)
    if exists(db, "review_deliveries"):
        counts = dict(db.execute("""SELECT count(*) AS prepared,
            coalesce(sum(observed IS NOT NULL),0) AS observed,
            coalesce(sum(observed IS NULL),0) AS unobserved,
            coalesce(sum(failure IS NOT NULL),0) AS recorded_failures,
            max(CASE WHEN observed IS NOT NULL THEN created END) AS last_observed_prepared_at
            FROM review_deliveries""").fetchone())
    counts.update(recent(db, counts["last_observed_prepared_at"]))
    return dict(counts, state=state(counts),
                in_process_automatic_sender=False, sent=None,
                action="Curator prepares digests but runs no sender. The scheduled originating-chat consumer must send and observe the complete native readback; preparation is not delivery. Sent-without-readback is not recorded.")


def report(db, root):
    return dict(state="checkpoint", collections=[coverage(db, r[0]) for r in db.execute("SELECT id FROM collections ORDER BY started")],
                notifications=notifications(db), organization=organization(db, root))
