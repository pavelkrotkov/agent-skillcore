from copy import deepcopy

from x_publication_fixtures import PublicationCase, events
from x_curator.evidence import bundle
from x_curator.executions import execute
from x_curator.packets import validate
from x_curator.receipts import digest
from x_curator.verdicts import approved


class EvidenceGateTests(PublicationCase):
    def test_fabricated_quote_or_capture_cannot_pass(self):
        for citation in ({"capture": "fabricated", "quote": "Synthetic evidence."},
                         {"capture": next(iter(self.evidence["captures"])), "quote": "Invented result"}):
            packet = deepcopy(self.packet)
            packet["claims"][0]["citations"] = [citation]
            with self.assertRaises((ValueError, KeyError)):
                validate(packet, self.evidence)

    def test_model_cannot_self_declare_an_independent_review(self):
        self.packet["reviewer"] = "independent"
        proposal = execute(self.db, self.token, "research", "synthetic", lambda _: events(self.packet, "same-session"))
        verdict = {"verdict": "approve", "proposal_sha": digest(self.packet), "bundle_sha": digest(self.evidence), "findings": []}
        review = execute(self.db, self.token, "review", "synthetic", lambda _: events(verdict, "same-session"), self.packet)
        with self.assertRaisesRegex(ValueError, "separate"):
            approved(self.db, self.token, proposal, review)

    def test_tampered_capture_and_acquisition_fail_closed(self):
        with self.db:
            self.db.execute("UPDATE captures SET payload='{}'")
        with self.assertRaisesRegex(ValueError, "tampered capture"):
            bundle(self.db, self.token)
        with self.db:
            self.db.execute("UPDATE responses SET body=?", (b'{}',))
        with self.assertRaisesRegex(ValueError, "tampered acquisition"):
            bundle(self.db, self.token)

    def test_execution_output_must_match_the_recorded_event_stream(self):
        proposal, review = self.approved_executions()
        with self.db:
            self.db.execute("UPDATE executions SET log=? WHERE id=?", (events({}), review))
        with self.assertRaisesRegex(ValueError, "tampered execution"):
            approved(self.db, self.token, proposal, review)
