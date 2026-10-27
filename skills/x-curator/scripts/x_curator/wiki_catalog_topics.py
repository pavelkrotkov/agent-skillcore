"""Choose catalog context from approved topics, preserving version identity."""
import re

from .wiki_keys import page_key


def selected_text(current, selected):
    return ' '.join(claim['text'] for key in selected for claim in current[key]['packet']['claims']).casefold()


def ranked_pages(pages, text, required):
    scored = [(page, score(page, text)) for page in pages.values()]
    candidates = [(page, rank) for page, rank in scored if eligible(page, rank, required)]
    return [page for page, _ in sorted(candidates, key=lambda item: (page_key(item[0]) not in required, item[1], page_key(item[0])))]


def eligible(page, rank, required):
    return not required or page_key(page) in required or not rank[0] or rank[1] <= -1


def score(page, text):
    names = [page['title'], *page.get('aliases', [])]
    words = set(re.findall(r'\w+', ' '.join(names).casefold()))
    matched = words & set(re.findall(r'\w+', text))
    versions = set(re.findall(r'\d+(?:\.\d+)*', page['title']))
    if not versions <= set(re.findall(r'\d+(?:\.\d+)*', text)):
        return True, 0
    named = any(named_match(name, text) for name in names if name)
    weight = 2 if page.get('entry') else 1
    return not named, -weight * len(matched) / max(1, len(words))


def named_match(name, text):
    left, right = ('', '') if re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', name) else (r'(?<![^\W\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af])', r'(?![^\W\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af])')
    return re.search(left + re.escape(name.casefold()) + right, text.casefold()) is not None
