"""Page-specific evidence links leave historical text-only rendering unchanged."""
from urllib.parse import urldefrag


def target(url, citation):
    pages = citation.get('pdf_pages')
    return urldefrag(url).url + '#page=' + str(pages[0]) if pages else url


def label(citation):
    pages = citation.get('pdf_pages')
    if not pages:
        return ''
    kind = 'visual observation' if citation.get('pdf_image') else 'text'
    return ' (PDF physical pages ' + ', '.join(map(str, pages)) + '; ' + kind + ')'
