import os
import sys
import time
import uuid
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator import model_events, quick_phase_runner
from x_curator.worker_prompts import prompt


class PhaseProcessTests(PublicationCase):
    def test_acquisition_cutoff_kills_cli_and_inflight_tool_child_but_preserves_input(self):
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        session = str(uuid.uuid4())
        sessions = self.root / 'sessions'
        sessions.mkdir()
        heartbeat = root / 'tool-heartbeat'
        child = 'import pathlib,time; p=pathlib.Path(%r)\nwhile True:\n p.write_text(str(time.time())); time.sleep(0.01)' % str(heartbeat)
        script = '''import sys,json,pathlib,subprocess,time
text=sys.stdin.read()
pathlib.Path(%r).write_text(json.dumps({'type':'session_meta','payload':{'id':%r}})+'\\n'+json.dumps({'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':text}]}}))
subprocess.Popen([sys.executable,'-c',%r])
print(json.dumps({'type':'thread.started','thread_id':%r}),flush=True)
time.sleep(30)
''' % (str(sessions / (session + '.jsonl')), session, child, session)
        started = time.time()
        request = dict(role='factcheck', policy='quick-factcheck/v1', bundle=self.evidence, proposal=None,
                       deadline=started + 3, phase=dict(name='evidence', cutoff=started + 0.4, image_policy='deferred-to-final'))
        environment = dict(os.environ, CODEX_HOME=str(self.root))
        with patch('x_curator.codex_runner.arguments', return_value=[sys.executable, '-c', script]):
            receipt = quick_phase_runner.capture(self.db, root, sys.executable, environment, request)
        self.assertEqual(receipt['status'], 'cutoff')
        self.assertLess(receipt['stopped'] - started, 1)
        self.assertLess(receipt['ended'], request['deadline'])
        self.assertEqual(receipt['input_proof']['prompt'], prompt(request))
        observed = heartbeat.read_bytes()
        time.sleep(0.1)
        self.assertEqual(heartbeat.read_bytes(), observed)
        with self.assertRaisesRegex(ValueError, 'incomplete model execution'):
            model_events.result(receipt['input_proof']['events'].encode())
