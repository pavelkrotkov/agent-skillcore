import unittest
from contextlib import nullcontext
from unittest.mock import patch
from x_curator import quick_window


class ReadWindowPolicyTests(unittest.TestCase):
    def test_approved_research_window_retains_its_own_deadline(self):
        row = dict(started=1000, deadline=1600, policy='approved-research/v1')
        with patch('x_curator.quick_window.quick_store.active', return_value=row), patch('time.time', return_value=1500), patch('x_curator.quick_window.until', return_value=nullcontext()) as timer:
            with quick_window.window(None, 'synthetic-approved-token'):
                timer.assert_called_once_with(row['deadline'])
