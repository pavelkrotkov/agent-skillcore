import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/x-curator/scripts"
sys.path.insert(0, str(SCRIPTS))

from x_curator.collect import collect
from x_curator.storage import open_store, selected_entries, sha256


def response(ids=(), cursor=None):
    entries = [tweet_entry(value) for value in ids]
    if cursor:
        entries.append({"entryId": "cursor-bottom-1", "content": {"value": cursor}})
    return envelope([{"type": "TimelineAddEntries", "entries": entries}])


def tweet_entry(value):
    return {"entryId": "tweet-" + value, "content": {"itemContent": {
        "tweet_results": {"result": {"__typename": "Tweet", "rest_id": value}}
    }}}


def envelope(instructions, kind="likes"):
    timeline = {"timeline": {"instructions": instructions}}
    data = {"user": {"result": {"timeline": timeline}}}
    if kind == "bookmarks":
        data = {"bookmark_timeline_v2": timeline}
    return json.dumps({"data": data}).encode()


class Client:
    account = "synthetic-account"

    def __init__(self, pages):
        self.pages = iter(pages)
        self.cursors = []

    def fetch(self, kind, cursor):
        self.cursors.append(cursor)
        item = next(self.pages)
        if isinstance(item, Exception):
            raise item
        return item

    def detail(self, source):
        return 200, json.dumps({'data': {'__typename': 'Tweet', 'rest_id': source,
                                        'legacy': {'full_text': 'Synthetic evidence.',
                                                   'user_id_str': 'author', 'conversation_id_str': source}}}).encode()


class CollectionCase(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = open_store(self.root)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
