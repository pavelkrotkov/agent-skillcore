"""Versioned immutable status and approval messages for originating-chat delivery."""
import json


def legacy(identity, batch):
    return '\n'.join(header(identity, batch) + questions(batch) + [reply(identity)])


def current(identity, batch):
    counts = batch['counts']
    failed = failures(batch)
    completed = sum(counts.get(key, 0) for key in ('supported', 'excluded', 'pending_decision'))
    rows = header(identity, batch) + [f"Status: useful notes {counts.get('supported', 0)}; completed factual checks {completed}; "
                                      f"technical failures {len(failed)}; still processing {counts.get('processing', 0)}."]
    if batch['review']:
        rows += ['\nResearch questions requiring explicit approval:'] + questions(batch)
    if failed:
        rows += ['\nTechnical failures (not research approval):']
        rows += [f"\n{item['reference']}\nFailure: {failure_text(item)}" for item in failed]
    rows.append(reply(identity) if batch['review'] else '\nNo research approval is requested by this digest.')
    return '\n'.join(rows)


def header(identity, batch):
    return [f"Likes review {identity}" + daily_label(batch), 'Batch results: ' + json.dumps(batch['counts'], sort_keys=True)]


def questions(batch):
    return [f"\n{item['reference']}\nQuestion: {item['question']}\nStopped: {item['reason']}\n"
            f"Scope: {item['scope']}\nMaximum: {item['seconds']} seconds." +
            (f"\nSeparately proposed {item['resource']['kind']} resource: {item['resource']['url']}" if item.get('resource') else '')
            for item in batch['review']]


def reply(identity):
    return (f'\nReply: review {identity}; research <reference>; defer <reference>; exclude <reference>. '
            'List multiple references with commas. Omitted items stay pending. '
            'Research approves only the question, scope and maximum shown; no automatic extension.')


def failures(batch):
    return [item for item in batch['items'] if item['state'] == 'failed_processing']


def failure_text(item): return '; '.join(item['retrieval_failures']) if isinstance(item.get('retrieval_failures'), list) and item['retrieval_failures'] else item['reason']


def daily_label(batch):
    return '\nDaily capture cutoff: ' + batch['cutoff_local'] if batch['kind'] == 'daily' else ''
