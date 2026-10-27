from x_retention_fixtures import RetentionCase
import json
from x_curator.storage import sha256


class RunRetentionCase(RetentionCase):
    def attempt(self, active=False):
        token = 'synthetic-run'
        old = self.now - 40 * 86400
        self.db.execute('INSERT INTO jobs(account,id,created,state,token) VALUES (?,?,?,?,?)',
                        ('account', 'source', old, 'leased' if active else 'published', token))
        self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',
                        (token, 'account', 'source', old, old + 60, None if active else old + 60,
                         'leased' if active else 'published', 'done'))
        identity = 'c' * 64
        events = json.dumps(dict(type='thread.started', thread_id='00000000-0000-4000-8000-000000000001')) + '\n'
        proof = dict(format='x-curator-input-proof-v2', request_sha=identity, events=events, rollout='canonical native transcript')
        log = json.dumps(proof).encode()
        self.db.execute('INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        ('execution', token, 'factcheck', 'model', '{}', identity, old, old + 60,
                         'session', '{}', sha256(b'{}'), log, sha256(log)))
        self.db.commit()
        folder = self.root / 'runs' / token
        folder.mkdir(parents=True)
        copied = folder / (identity + '.jsonl')
        copied.write_text(events)
        self.age(copied)
        (self.root / 'blobs').mkdir()
        original = self.root / 'blobs' / ('d' * 64)
        original.write_bytes(b'original image')
        image = folder / (original.name + '.png')
        image.write_bytes(original.read_bytes())
        self.age(image)
        sessions = self.root / 'worker/sessions'
        sessions.mkdir(parents=True)
        # The canonical envelope must retain the exact native bytes before a copy expires.
        transcript = sessions / 'rollout-00000000-0000-4000-8000-000000000001.jsonl'
        transcript.write_text(proof['rollout'])
        self.age(transcript)
        return copied, image, transcript, original, log
