import json

from x_operational_fixtures import OperationalCase
from x_curator import operational_status


class GraphStatusTests(OperationalCase):
    def test_active_source_map_reports_mapping_gap_and_pending_indexing(self):
        self.generation({"mapped":["concepts/synthetic"],"source-only":[]})
        self.db.executemany("INSERT INTO publications(id,state) VALUES (?,?)",
                           [("mapped","published"),("source-only","published"),("new","published")])
        self.db.executemany("INSERT INTO wiki_runs VALUES (?,?,?)",
                           [("accepted","accepted",10),("failed","failed",20)])
        before = self.db.total_changes
        status = operational_status.organization(self.db, self.root)
        self.assertEqual((status["sources_indexed"],status["sources_mapped"],status["sources_unmapped"]), (2,1,1))
        self.assertEqual(status["sources_awaiting_index"], 1)
        self.assertEqual(status["last_accepted_organization"], dict(id="accepted",started=10))
        self.assertEqual(status["state"], "recorded")
        self.assertFalse(status["proof_audited"])
        self.assertEqual(self.db.total_changes, before)

    def test_damaged_source_map_never_claims_complete_mapping(self):
        path = self.generation({"source-only":[]})
        path.write_text('{"source-only":["invented"]}')
        status = operational_status.organization(self.db, self.root)
        self.assertEqual(status["state"], "unavailable")
        self.assertIsNone(status["sources_mapped"])
        self.assertIn("hash", status["action"])
        self.assertEqual(json.loads((self.root/"wiki/CURRENT.json").read_text())["generation"], "synthetic")
