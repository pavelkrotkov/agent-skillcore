"""Paragraph-aware version-one boundaries preserve every original character."""

def split(text, width):
    start = 0
    if not text:
        yield 0, 0
    while start < len(text):
        end = boundary(text, start, min(len(text), start + width))
        yield start, end
        start = end


def boundary(text, start, stop):
    if stop == len(text):
        return stop
    lower = start + (stop - start) // 2
    for delimiter in ('\n\n', '.\n', '. '):
        found = text.rfind(delimiter, lower, stop)
        if found >= 0:
            return found + len(delimiter)
    return stop


def context(text, start, end, size):
    left = max(0, start - size)
    paragraph = text.find('\n\n', left, start)
    if paragraph >= 0:
        left = paragraph + 2
    right = boundary(text, end, min(len(text), end + size))
    return left, right
