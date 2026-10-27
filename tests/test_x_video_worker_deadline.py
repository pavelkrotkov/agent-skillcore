from configparser import ConfigParser
from pathlib import Path
import shlex
import time
from unittest.mock import patch

from x_video_fixtures import PreparedVideoCase
from x_curator import cli, prepared_video
from x_curator.worker_process import process


class VideoWorkerDeadlineTests(PreparedVideoCase):
    def test_deployed_worker_survives_full_video_budget_with_cleanup_headroom(self):
        prepared_video.store(self.db, self.job, self.payload(), 'Synthetic approval')
        config = ConfigParser(interpolation=None)
        config.read(Path(__file__).resolve().parents[1] /
                    'skills/x-curator/templates/systemd/x-curator-worker@.service')
        command = shlex.split(config['Service']['ExecStart'])
        with patch('sys.argv', ['x-curator', *command[command.index('--state'):]]):
            options = cli.arguments()
        started = time.time()
        self.db.execute('UPDATE jobs SET lease_until=? WHERE token=?', (started + options.lease_seconds, self.token))
        job = dict(self.db.execute('SELECT * FROM jobs WHERE token=?', (self.token,)).fetchone())
        receipts = []
        def check(db, state, client, token, receipt):
            receipts.append(receipt)
        with patch('time.time', return_value=started), patch('x_curator.quick_process.run', side_effect=check) as run:
            process(self.db, self.root, None, job)
        run.assert_called_once()
        self.assertEqual(receipts[0]['deadline'], started + 180)
        self.assertGreaterEqual(job['lease_until'] - receipts[0]['deadline'], 60)
        self.assertGreaterEqual(started + float(config['Service']['TimeoutStartSec']) - receipts[0]['deadline'], 60)
