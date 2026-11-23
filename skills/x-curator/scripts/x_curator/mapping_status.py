"""Read recorded mapping allowances without initializing or changing them."""
from .retention_files import table


def status(db):
    if not table(db, 'wiki_sources'):
        return dict(mapping_eligible=None, mapping_exhausted=None, mapping_failure_reasons=[])
    grants = '(SELECT count(*) FROM wiki_recovery_grants WHERE publication=p.id)' if table(db, 'wiki_recovery_grants') else '0'
    rows = db.execute("""SELECT coalesce(s.attempts,0)<3+""" + grants + """ AS eligible,
        s.action,count(*) AS sources FROM publications p JOIN jobs j ON j.account=p.account AND j.id=p.source
        LEFT JOIN wiki_sources s ON s.publication=p.id
        WHERE p.state='published' AND j.state='published' AND s.run IS NULL GROUP BY eligible,s.action""").fetchall()
    reasons = failure_reasons(rows)
    return dict(mapping_eligible=sum(row['sources'] for row in rows if row['eligible']),
                mapping_exhausted=sum(row['sources'] for row in rows if not row['eligible']),
                mapping_failure_reasons=reasons)


def failure_reasons(rows):
    counts = {}
    for row in rows:
        if row['action'] and row['action'] != 'organize verified claims':
            action = row['action'][:200]
            counts[action] = counts.get(action, 0) + row['sources']
    return [dict(action=action, sources=count) for action, count in
            sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]
