import json
import uuid

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry
from x_curator.evidence import bundle, capture_selection
from x_curator.executions import execute
from x_curator.leases import claim
from x_curator.queue import enqueue
from x_curator.receipts import digest


def events(packet, session=None):
    values = [{"type": "thread.started", "thread_id": session or uuid.uuid4().hex},
              {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(packet)}},
              {"type": "turn.completed", "usage": {}}]
    return "\n".join(json.dumps(v) for v in values).encode()


class PublicationCase(CollectionCase):
    def setUp(self):
        super().setUp()
        entry = tweet_entry("1")
        entry["content"]["itemContent"]["tweet_results"]["result"]["core"] = {"user_results": {"result": {"rest_id": "author", "legacy": {"pinned_tweet_ids_str": ["2"]}}}}
        entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"] = {"full_text": "Synthetic evidence."}
        collect(self.db, Client([(200, envelope([{"type": "TimelineAddEntries", "entries": [entry]}]))]), "likes", delay=0)
        enqueue(self.db)
        self.token = claim(self.db, Client.account)["token"]
        capture = capture_selection(self.db, self.token)
        self.evidence = bundle(self.db, self.token)
        self.packet = {"source": "1", "bundle_sha": digest(self.evidence),
                       "title": {"text": "Synthetic source", "claims": ["c1"]},
                       "summary": {"text": "The author provides synthetic evidence.", "claims": ["c1"]},
                       "claims": [{"id": "c1", "text": "The author provides synthetic evidence.", "kind": "opinion",
                                   "attribution": "Synthetic author", "limitations": [],
                                   "citations": [{"capture": capture, "quote": "Synthetic evidence."}]}],
                       "limitations": [], "coverage": [{"capture": capture, "status": "covered", "notes": "Text reviewed."}]}

    def approved_executions(self):
        proposal = execute(self.db, self.token, "research", "synthetic", lambda _: events(self.packet))
        verdict = {"verdict": "approve", "proposal_sha": digest(self.packet), "bundle_sha": digest(self.evidence), "findings": []}
        review = execute(self.db, self.token, "review", "synthetic", lambda _: events(verdict), self.packet)
        return proposal, review
