"""Unspent-only dispatch holds consumed work without resetting any receipt or budget."""


def hold_spent(db, account):
    db.execute("""UPDATE jobs SET state='needs_action',action='spent attempt held; explicit recovery approval required',
        token=NULL,lease_until=NULL WHERE account=? AND attempts>0 AND state IN ('pending','retry')""", (account,))
