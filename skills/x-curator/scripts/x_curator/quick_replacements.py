"""Approved replacements append history; source attempts bound chain resolution."""


def migrate(db):
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name='quick_recoveries'").fetchone()[0]
    legacy = ', UNIQUE(account,source)'
    if legacy not in sql:
        return
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute(sql.replace('quick_recoveries', 'quick_recoveries_next', 1).replace(legacy, ''))
        db.execute('INSERT INTO quick_recoveries_next SELECT * FROM quick_recoveries')
        db.execute('DROP TABLE quick_recoveries')
        db.execute('ALTER TABLE quick_recoveries_next RENAME TO quick_recoveries')


def latest(db, account, source, identity):
    job = db.execute('SELECT max_attempts FROM jobs WHERE account=? AND id=?', (account, source)).fetchone()
    if job is None:
        raise ValueError('replacement source job is missing')
    for _ in range(job[0]):
        row = db.execute('SELECT * FROM quick_recoveries WHERE original=?', (identity,)).fetchone()
        if row is None:
            return identity
        if (row['account'], row['source']) != (account, source):
            raise ValueError('replacement belongs to another source')
        identity = row['replacement']
    raise ValueError('replacement chain exceeds the source attempt bound')
