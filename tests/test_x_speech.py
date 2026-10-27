import io
import json
import wave
from unittest.mock import Mock, patch

from x_publication_fixtures import PublicationCase
from x_curator.speech_audio import duration
from x_curator.speech_protocol import make_receipt, validate
from x_curator.speech_http import Handler
from x_curator.storage import sha256


def audio():
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0' * 32000)
    return output.getvalue()


class SpeechTests(PublicationCase):
    def test_receipt_requires_exact_audio_and_qualified_profile(self):
        body = audio()
        config = {'engine_sha': 'engine', 'model_sha': 'model'}
        receipt = dict(config, audio_sha=sha256(body), duration=1.0, segments=[{'start': 0, 'end': 1, 'text': 'synthetic'}])
        self.assertEqual(validate(receipt, body, config), receipt)
        with self.assertRaisesRegex(ValueError, 'different audio'):
            validate(dict(receipt, audio_sha='foreign'), body, config)
        with self.assertRaisesRegex(ValueError, 'qualified profile'):
            validate(dict(receipt, model_sha='other'), body, config)
        with self.assertRaisesRegex(ValueError, 'outside input'):
            validate(dict(receipt, segments=[{'start': 0, 'end': 999, 'text': 'wrong duration'}]), body, config)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            duration(body[:-4])

    def test_bounded_final_timestamp_overrun_uses_exact_audio_duration(self):
        body = audio()
        config = {'engine_sha': 'engine', 'model_sha': 'model'}
        output = {'transcription': [{'offsets': {'from': 0, 'to': 25000}, 'text': ' synthetic '}]}
        receipt = make_receipt(output, config, body, 1.0, 0)
        self.assertEqual(receipt['segments'], [{'start': 0.0, 'end': 1.0, 'text': 'synthetic'}])
        self.assertEqual(validate(receipt, body, config), receipt)
        output['transcription'][0]['offsets']['to'] = 32000
        with self.assertRaisesRegex(ValueError, 'outside input'):
            validate(make_receipt(output, config, body, 1.0, 0), body, config)

    def test_unauthorized_or_partial_audio_cannot_reach_the_engine(self):
        handler = object.__new__(Handler)
        handler.path = '/transcribe'
        handler.command = 'POST'
        handler.server = Mock(config={'token': 'private-test-token'})
        handler.headers = {'Authorization': 'Bearer wrong', 'Content-Length': str(len(audio()))}
        handler.rfile = io.BytesIO(audio())
        with patch('x_curator.speech_http.transcribe') as engine:
            with self.assertRaisesRegex(ValueError, 'invalid speech request'):
                handler.process()
            handler.headers['Authorization'] = 'Bearer private-test-token'
            handler.rfile = io.BytesIO(audio()[:-4])
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                handler.process()
        engine.assert_not_called()
