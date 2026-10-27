import time
from unittest.mock import patch
from x_quick_fixtures import QuickCase
from x_curator import quick_sources,quick_store


class WindowCase(QuickCase):
    def setUp(self):
        super().setUp()
        self.start = self.at = time.time()
        quick_store.start(self.db, self.token, self.start)
        self.clock = patch('time.time', side_effect=lambda: self.at)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.source = quick_sources.source(self.db, self.token, 'https://example.test/release')
