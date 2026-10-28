from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest

from x_fixtures import CollectionCase
from x_lock_fixtures import competing_index
from x_curator import __main__ as cli, stage_timings
from x_curator.command_lock import command_lock


class IndexLockTests(CollectionCase):
    def invoke(self, dispatch=None):
        args = SimpleNamespace(state=self.root, command='index-pending')
        stdout, stderr = StringIO(), StringIO()
        with patch.object(cli, 'arguments', return_value=args), patch.object(cli, 'dispatch', dispatch):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_busy_index_defers_then_next_invocation_dispatches(self):
        dispatch = unittest.mock.Mock(return_value={'state': 'idle'})
        with competing_index(self.root, 30):
            code, stdout, stderr = self.invoke(dispatch)
        self.assertEqual((code, json.loads(stdout)['state'], stderr), (0, 'pending', ''))
        dispatch.assert_not_called()
        spans = stage_timings.report(self.db)['aggregates']
        self.assertEqual(spans['wiki.index_entry']['outcomes']['skipped'], 1)
        self.assertEqual(self.invoke(dispatch)[0], 0)
        dispatch.assert_called_once()

    def test_dispatch_blocking_io_error_is_not_acquisition_contention(self):
        dispatch = unittest.mock.Mock(side_effect=BlockingIOError('internal operation'))
        code, stdout, stderr = self.invoke(dispatch)
        self.assertEqual((code, stdout, json.loads(stderr)['error']), (1, '', 'BlockingIOError'))
        dispatch.assert_called_once()

    def test_other_commands_and_acquisition_errors_still_fail(self):
        args = SimpleNamespace(state=self.root, command='wiki')
        with competing_index(self.root, 30), self.assertRaises(BlockingIOError):
            with command_lock(args):
                self.fail('busy wiki must not run')
        dispatch = unittest.mock.Mock()
        with patch('x_curator.command_lock.fcntl.flock', side_effect=PermissionError('denied')):
            code, stdout, stderr = self.invoke(dispatch)
        self.assertEqual((code, stdout, json.loads(stderr)['error']), (1, '', 'PermissionError'))
        dispatch.assert_not_called()
