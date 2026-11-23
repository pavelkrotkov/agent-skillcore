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

    def test_mapping_status_counts_eligible_and_exhausted_without_mutating_budgets(self):
        self.db.executescript("""
            CREATE TABLE wiki_sources(publication TEXT, attempts INTEGER, run TEXT, action TEXT);
            CREATE TABLE wiki_recovery_grants(publication TEXT);
            INSERT INTO publications(id,state) VALUES ('new','published'),('spent','published'),
                ('granted','published'),('mapped','published'),('withdrawn','withdrawn'),('held','published');
            UPDATE publications SET account='account',source=id;
            INSERT INTO jobs SELECT account,source,'published' FROM publications;
            UPDATE jobs SET state='needs_action' WHERE id='held';
            INSERT INTO wiki_sources VALUES ('spent',3,NULL,'DeadlineExceeded'),
                ('granted',3,NULL,'rejected'),('mapped',1,'accepted','verified'),
                ('withdrawn',3,NULL,'rejected');
            INSERT INTO wiki_recovery_grants VALUES ('granted');
        """)
        before = self.db.total_changes
        value = operational_status.organization(self.db)
        self.assertEqual((value['mapping_eligible'], value['mapping_exhausted']), (2, 1))
        self.assertEqual(value['mapping_failure_reasons'], [dict(action='DeadlineExceeded', sources=1),
                                                           dict(action='rejected', sources=1)])
        self.assertEqual(self.db.total_changes, before)
