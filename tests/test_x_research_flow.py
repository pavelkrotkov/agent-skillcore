from copy import deepcopy
from unittest.mock import patch

from x_publication_fixtures import PublicationCase, events
from x_curator.receipts import digest
from x_curator.worker import process
from x_curator.research import research


class ResearchFlowTests(PublicationCase):
    def setUp(self):
        super().setUp()
        override = patch("x_curator.worker_process.research", research)
        override.start()
        self.addCleanup(override.stop)

    def model(self, request):
        if request["role"] == "discover":
            return events({"urls": ["https://example.org/primary"], "notes": "Primary source."})
        if request["role"] == "review":
            return events({"verdict": "approve", "proposal_sha": digest(request["proposal"]),
                           "bundle_sha": request["bundle_sha"], "findings": []})
        packet = deepcopy(self.packet)
        packet["bundle_sha"] = request["bundle_sha"]
        packet["coverage"] = [{"capture": key, "status": "covered", "notes": "Read evidence."}
                              for key in request["bundle"]["captures"]]
        return events(packet)

    def test_whole_controller_flow_records_acquisition_and_separate_review(self):
        job = dict(self.db.execute("SELECT * FROM jobs").fetchone())
        def fetch(_):
            return 200, "text/html", b"<article>Primary source with synthetic evidence.</article>", None
        with patch("x_curator.research.runner", return_value=self.model), patch("x_curator.research.source_fetcher", return_value=fetch):
            result = process(self.db, self.root, None, job)
        self.assertEqual(result["state"], "published", result)
        self.assertEqual(self.db.execute("SELECT count(*) FROM retrievals").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT count(DISTINCT session) FROM executions").fetchone()[0], 3)
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "published")

    def test_malformed_model_packet_cannot_become_a_wiki_page(self):
        job = dict(self.db.execute("SELECT * FROM jobs").fetchone())
        def fetch(_):
            return 200, "text/plain", b"Source text with sufficient context.", None
        with patch("x_curator.research.runner", return_value=lambda _: events({})), patch("x_curator.research.source_fetcher", return_value=fetch):
            result = process(self.db, self.root, None, job)
        self.assertEqual(result["state"], "retry")
        self.assertEqual(self.db.execute("SELECT count(*) FROM publications").fetchone()[0], 0)
