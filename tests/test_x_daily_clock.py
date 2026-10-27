from datetime import datetime
from zoneinfo import ZoneInfo
import unittest

from x_curator import daily_plan


class DailyClockTests(unittest.TestCase):
    def test_local_midnights_follow_both_dst_transitions(self):
        zone = ZoneInfo('America/New_York')
        def boundary(day):
            now = datetime.fromisoformat(day + 'T12:00:00').replace(tzinfo=zone).timestamp()
            return daily_plan.cutoff(now, zone.key)
        self.assertEqual(boundary('2026-03-09') - boundary('2026-03-08'), 23 * 3600)
        self.assertEqual(boundary('2026-11-02') - boundary('2026-11-01'), 25 * 3600)
