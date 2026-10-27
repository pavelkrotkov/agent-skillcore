from copy import deepcopy

from x_fixtures import Client, collect, envelope, tweet_entry
from x_publication_fixtures import PublicationCase
from x_curator.evidence import bundle, capture_selection
from x_curator.packets import validate
from x_curator.receipts import digest
from x_curator.source_requirements import requirements
from x_curator.verdicts import approved
from x_curator.publication import publish
from x_curator.publication_audit import audit
from x_curator.queue import enqueue


class EvidenceRevisionTests(PublicationCase):
    def test_adding_a_new_capture_cannot_hide_an_old_source_revision(self):
        entry = tweet_entry("1")
        entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"] = {"full_text": "New revision."}
        body = envelope([{"type": "TimelineAddEntries", "entries": [entry]}])
        collect(self.db, Client([(200, body)]), "likes", new=True, delay=0)
        capture_selection(self.db, self.token)
        with self.assertRaisesRegex(ValueError, "revision changed"):
            bundle(self.db, self.token)

    def test_source_changes_invalidate_an_already_approved_packet(self):
        proposal, review = self.approved_executions()
        entry = tweet_entry("1")
        entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"] = {"full_text": "Edited source."}
        body = envelope([{"type": "TimelineAddEntries", "entries": [entry]}])
        collect(self.db, Client([(200, body)]), "likes", new=True, delay=0)
        with self.assertRaisesRegex(ValueError, "revision changed"):
            approved(self.db, self.token, proposal, review)

    def test_unacquired_media_cannot_be_omitted_from_coverage(self):
        evidence = deepcopy(self.evidence)
        capture = next(iter(evidence["captures"].values()))
        capture["required_urls"] = ["https://example.org/essential-video.mp4"]
        packet = deepcopy(self.packet)
        packet["bundle_sha"] = digest(evidence)
        with self.assertRaisesRegex(ValueError, "has not been acquired"):
            validate(packet, evidence)

    def test_source_media_links_and_context_are_controller_obligations(self):
        entry = tweet_entry("1")
        tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
        tweet["legacy"] = {"in_reply_to_status_id_str": "2", "entities": {"urls": [{"expanded_url": "https://example.org/paper"}]},
                           "extended_entities": {"media": [{"type": "photo", "media_url_https": "https://example.org/figure.jpg"}]}}
        self.assertEqual(requirements(entry), ["https://example.org/figure.jpg", "https://example.org/paper", "https://x.com/i/status/2"])

    def test_long_post_and_unavailable_quote_remain_obligations(self):
        entry = tweet_entry("1")
        tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
        tweet["legacy"] = {"quoted_status_id_str": "2"}
        tweet["note_tweet"] = {"note_tweet_results": {"result": {"entity_set": {"urls": [{"expanded_url": "https://example.org/primary"}]}}}}
        self.assertEqual(requirements(entry), ["https://example.org/primary", "https://x.com/i/status/2"])

    def test_source_edit_reopens_published_work_without_deleting_version(self):
        proposal, review = self.approved_executions()
        publication = publish(self.db, self.root, self.token, proposal, review)
        entry = tweet_entry("1")
        entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"] = {"full_text": "Changed after publication."}
        collect(self.db, Client([(200, envelope([{"type": "TimelineAddEntries", "entries": [entry]}]))]), "likes", new=True, delay=0)
        enqueue(self.db)
        self.assertEqual(audit(self.db, self.root), [publication])
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "retry")
        self.assertIn('recapture and re-review', self.db.execute("SELECT action FROM jobs").fetchone()[0])
        row = self.db.execute("SELECT path,body FROM publications").fetchone()
        self.assertEqual((self.root / row[0]).read_bytes(), row[1])
