"""Reject changed histories, source revisions, decisions and previous replacements."""
from repair_history import snapshot
from x_curator.receipts import digest
from x_curator.revisions import revision
from x_curator.source_evidence import selected_source


def job(db, item):
    row = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (item['account'], item['source'])).fetchone()
    if row is None:
        raise ValueError('missing qualification job')
    return dict(row)


def undecided(db, item):
    key = (item['account'], item['source'])
    permission = db.execute('SELECT 1 FROM research_permissions WHERE account=? AND source=?', key).fetchone()
    decision = db.execute('''SELECT 1 FROM review_decisions d JOIN review_deliveries v ON v.id=d.delivery
        WHERE json_extract(v.payload,'$.account')=? AND substr(d.reference,instr(d.reference,':')+1)=?''', key).fetchone()
    if permission or decision:
        raise ValueError('qualification item has a human decision or research permission')


def unchanged(db, item):
    frozen = {key: item[key] for key in ('original_sha', 'tools', 'executions', 'prior_attempts')}
    if snapshot(db, item) != frozen:
        raise ValueError('qualification history changed; inspect a fresh preview')
    current = job(db, item)
    if digest(revision(selected_source(db, current)['entry'])) != item['revision']:
        raise ValueError('qualification source revision changed')
    undecided(db, item)
    return current


def eligible(db, item):
    current = unchanged(db, item)
    latest = db.execute('''SELECT id,outcome,revision FROM quick_checks WHERE account=? AND source=?
        ORDER BY started DESC,id DESC LIMIT 1''', (item['account'], item['source'])).fetchone()
    if (latest['id'], latest['outcome'], latest['revision']) != (item['original'], 'inconclusive', item['revision']):
        raise ValueError('qualification requires the latest inconclusive check')
    if (current['state'], current['attempts'], current['max_attempts'], digest(current)) != (
            'awaiting_review', item['attempts'], item['max_attempts'], item['job_sha']):
        raise ValueError('qualification job changed; inspect a fresh preview')
    if db.execute('SELECT 1 FROM quick_recoveries WHERE account=? AND source=?',
                  (item['account'], item['source'])).fetchone():
        raise ValueError('qualification cannot replace a previous replacement')
    return current
