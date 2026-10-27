"""Qualification uses the ordinary distinction between questions and tool failures."""
from x_curator import batch_items, native_search, native_search_trace, policy_timings, quick_failures
from x_curator.receipts import digest


def actual_queries(db, identity):
    try:
        rows = db.execute("SELECT log FROM executions WHERE json_extract(input,'$.check')=? ORDER BY started,id", (identity,))
        return [query for row in rows for query in native_search_trace.usage(row['log'] or b'')['queries']]
    except (ValueError, UnicodeError, KeyError, TypeError):
        return None


def measurement(db, check):
    value = policy_timings.measure(db, check, 'check', native_search.limit(db, check['token']))
    elapsed = value['processing_seconds']
    value.update(queries=actual_queries(db, check['id']), deadline_met=elapsed is not None and
                 not value['unfinished_receipts'] and elapsed <= value['allowance_seconds'] and not value['overruns'])
    return value


def outcomes(db, manifest):
    values = []
    for item in manifest['items']:
        replacement = digest(['retrieval-repair/v1', item['original']])
        check = db.execute('SELECT * FROM quick_checks WHERE id=?', (replacement,)).fetchone()
        row = dict(db.execute('SELECT * FROM jobs WHERE account=? AND id=?',
                              (item['account'], item['source'])).fetchone())
        failures = quick_failures.retrieval(db, check['token']) if check else []
        row.update(outcome=check['outcome'] if check else None, reason=check['reason'] if check else None,
                   execution=check['execution'] if check else None)
        values.append(dict(source=item['source'], category=item['category'], state=row['state'],
                           outcome=row['outcome'], reason=row['reason'], execution=row['execution'],
                           disposition=batch_items.disposition(row, failures), retrieval_failures=failures,
                           prior_reason=item.get('prior_reason'), attempt_spent=row['attempts'] > item['attempts'],
                           metrics=measurement(db, dict(check)) if check else None))
    return values
