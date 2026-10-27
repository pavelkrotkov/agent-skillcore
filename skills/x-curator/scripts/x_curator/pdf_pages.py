"""Physical pages retain exact extraction offsets, including text-empty pages."""
import struct


def intervals(text, count):
    parts = text.split('\f')
    if not 1 <= count <= 512 or len(parts) != count + 1 or parts[-1] != '':
        raise ValueError('PDF physical pages do not match complete text extraction')
    start = 0
    for number, content in enumerate(parts[:-1], 1):
        end = start + len(content) + 1
        yield {'number': number, 'start': start, 'end': end}
        start = end


def dimensions(body):
    if len(body) < 24 or body[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
        raise ValueError('PDF renderer did not return a PNG page')
    width, height = struct.unpack('>II', body[16:24])
    if not 0 < min(width, height) <= max(width, height) <= 1600:
        raise ValueError('PDF page pixels exceed the qualified renderer dimensions')
    return width, height
