from x_publication_fixtures import events
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator.evidence import bundle, capture_selection
from x_curator.executions import execute
from x_curator.leases import claim
from x_curator.publication import publish
from x_curator.queue import enqueue
from x_curator.receipts import digest


def publish_arrival(db, root, source='2'):
    entry = tweet_entry(source)
    entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'New synthetic opinion.'}
    collect(db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', new=True, delay=0)
    enqueue(db)
    token = claim(db, Client.account)['token']
    capture = capture_selection(db, token)
    evidence = bundle(db, token)
    packet = {'source': source, 'bundle_sha': digest(evidence),
              'title': {'text': 'New opinion', 'claims': ['c1']},
              'summary': {'text': 'New synthetic opinion.', 'claims': ['c1']},
              'claims': [{'id': 'c1', 'text': 'New synthetic opinion.', 'kind': 'opinion',
                          'attribution': 'Synthetic author', 'limitations': [],
                          'citations': [{'capture': capture, 'quote': 'New synthetic opinion.'}]}],
              'limitations': [], 'coverage': [{'capture': capture, 'status': 'covered', 'notes': 'Text reviewed.'}]}
    proposal = execute(db, token, 'research', 'synthetic', lambda _: events(packet))
    verdict = {'verdict': 'approve', 'proposal_sha': digest(packet), 'bundle_sha': digest(evidence), 'findings': []}
    review = execute(db, token, 'review', 'synthetic', lambda _: events(verdict), packet)
    return publish(db, root, token, proposal, review)
