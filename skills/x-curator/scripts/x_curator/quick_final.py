"""A completed final reference selects an exact successful draft from its own execution."""
import json
import time
from .receipts import digest
from .verification_details import hash_label

FORMAT = 'curator-validated-decision-v1'


def receipt(db, token, decision):
    value = {'valid': True, 'note': 'Draft only. Final submission still requires full execution and publication verification.'}
    row = db.execute("SELECT input FROM executions WHERE token=? AND role='factcheck' AND finished IS NULL ORDER BY started DESC,id DESC LIMIT 1", (token,)).fetchone()
    if row and json.loads(row['input']).get('final_format') == FORMAT:
        from .quick_store import active
        final = dict(format=FORMAT, decision_sha=digest(decision))
        value.update(decision_sha=final['decision_sha'], final_answer=final,
                     next_action='Return final_answer verbatim as your final response now. No further tools or analysis.',
                     remaining_seconds=max(0, int(active(db, token)['deadline']-time.time())))
    return value


def output(db, execution):
    row = db.execute('SELECT * FROM executions WHERE id=?', (execution,)).fetchone()
    value = json.loads(row['output'])
    if value.get('format') != FORMAT:
        return value
    request = json.loads(row['input'])
    if (row['role'], request.get('policy'), request.get('final_format'), set(value)) != ('factcheck', 'quick-factcheck/v1', FORMAT, {'format', 'decision_sha'}):
        raise ValueError('final reference needs its explicit quick-check output contract')
    if hash_label(value['decision_sha']) == 'invalid':
        raise ValueError('final reference needs a valid decision hash')
    validation = db.execute('''SELECT arguments,output FROM quick_tools
        WHERE token=? AND name='validate' AND created>=? AND finished<=?
        AND json_extract(output,'$.isError')=0
        AND json_extract(json_extract(output,'$.content[0].text'),'$.decision_sha')=?
        ORDER BY created DESC,id DESC LIMIT 1''', (row['token'], row['started'], row['finished'], value['decision_sha'])).fetchone()
    if validation is None:
        raise ValueError('final reference has no successful validation in this execution')
    decision = json.loads(validation['arguments'])['decision']
    response = json.loads(json.loads(validation['output'])['content'][0]['text'])
    if (response.get('valid'), digest(decision)) != (True, value['decision_sha']):
        raise ValueError('validated decision reference changed')
    return decision
