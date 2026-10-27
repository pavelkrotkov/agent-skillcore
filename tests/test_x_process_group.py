import time
import subprocess
import sys
from x_curator import process_group
from x_curator.deadlines import DeadlineExceeded, until
from x_publication_fixtures import PublicationCase


class ProcessGroupTests(PublicationCase):
    def test_wall_clock_kills_cli_process_group_on_timeout(self):
        pid_file = self.root / 'child.pid'
        script = "import os,time,pathlib; pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(30)" % str(pid_file)
        started = time.monotonic()
        with self.assertRaises(DeadlineExceeded):
            with until(time.time() + 0.25):
                process_group.run([sys.executable, '-c', script], b'', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertLess(time.monotonic() - started, 2)
        import os
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
