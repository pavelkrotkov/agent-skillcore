from pathlib import Path
from unittest.mock import patch

from x_operational_fixtures import OperationalCase
from x_curator import operational_status


class OperationalStatusTests(OperationalCase):
    def test_prepared_messages_need_an_external_consumer_without_invented_send_failures(self):
        self.db.executemany("INSERT INTO review_deliveries VALUES (?,?,?,?)",
                           [("prepared",None,None,1),("observed","native receipt",None,2),
                            ("failed",None,"platform unavailable",3)])
        before = self.db.total_changes
        status = operational_status.notifications(self.db)
        self.assertEqual({key:status[key] for key in ("prepared","observed","unobserved","recorded_failures")},
                         dict(prepared=3,observed=1,unobserved=2,recorded_failures=1))
        self.assertFalse(status["in_process_automatic_sender"])
        self.assertEqual(status["state"], "external_consumer_required")
        self.assertIsNone(status["sent"])
        self.assertEqual(status["last_observed_prepared_at"], 2)
        self.assertEqual(self.db.total_changes, before)
        self.assertIsNone(self.db.execute("SELECT failure FROM review_deliveries WHERE id='prepared'").fetchone()[0])

    def test_unknown_tables_and_empty_outbox_do_not_claim_a_delivery_failure(self):
        self.assertEqual(operational_status.notifications(self.db)["state"], "idle")
        self.db.execute("DROP TABLE review_deliveries")
        self.assertEqual(operational_status.notifications(self.db)["prepared"], 0)

    def test_status_command_exposes_operational_summary_without_source_audits(self):
        from x_curator.__main__ import dispatch
        from types import SimpleNamespace
        args = SimpleNamespace(command="status",state=self.root)
        with patch("x_curator.accounting.audit",side_effect=AssertionError("No proof audit")):
            status = dispatch(self.db,args)
        self.assertEqual(status["collections"], [])
        self.assertIn("notifications", status)
        self.assertEqual(status["organization"]["state"], "absent")

    def test_service_enables_bounded_organization_while_index_entry_remains_model_free(self):
        root = Path(__file__).resolve().parents[1]
        service = (root/"skills/x-curator/templates/systemd/x-curator-fresh.service").read_text()
        self.assertIn("supervise --max-items 0 --max-sources 5 --seconds 3500", service)
        from x_curator import index_pending
        with patch.object(index_pending.queue,"initialize"),patch.object(index_pending.receipts,"initialize"),patch.object(index_pending.wiki_store,"initialize"):
            with patch.object(index_pending,"previous",return_value={"previous"}),patch.object(index_pending,"wiki",return_value={"state":"checkpoint"}) as build:
                index_pending.run.__wrapped__(self.db,self.root)
        build.assert_called_once_with(self.db,self.root,0)

    def test_old_unobserved_deliveries_are_separate_from_pending_current_delivery(self):
        self.db.executemany("INSERT INTO review_deliveries VALUES (?,?,?,?)",
                           [('old',None,'old failure',1),('read','native readback',None,2)])
        value = operational_status.notifications(self.db)
        self.assertEqual(value['state'], 'historical_unobserved')
        self.assertEqual(value['pending_since_last_observed'], 0)
        self.assertEqual(value['failures_since_last_observed'], 0)
        self.db.execute("INSERT INTO review_deliveries VALUES ('new',NULL,'new failure',3)")
        value = operational_status.notifications(self.db)
        self.assertEqual(value['pending_since_last_observed'], 1)
        self.assertEqual(value['failures_since_last_observed'], 1)
