"""Cached trace records are copied without decoding large JSON strings again."""
import json
from unittest import TestCase
from unittest.mock import patch
from x_curator import model_trace


class TraceCacheCodecTests(TestCase):
    def test_repeated_records_parse_only_original_lines_and_isolate_nested_mutation(self):
        expected = [{'type': 'cache-codec-fixture', 'payload': {'text': 'a\u2028b\x00c', 'nested': [True, None, 1.25]}}]
        body = json.dumps(expected[0], ensure_ascii=False).encode()+b'\n'
        model_trace.decoded.cache_clear()
        with patch.object(model_trace.json, 'loads', wraps=json.loads) as parse:
            first = model_trace.records(body)
            first[0]['payload']['nested'].append('mutated')
            self.assertEqual(model_trace.records(body), expected)
        self.assertEqual(parse.call_count, 1)
