"""Append explicit article qualifications bound to one exact collection receipt."""
import time

from . import article_currentness, blobs
from .receipts import digest
from .article_qualification_store import retained
from .source_evidence import selected_source


def selection(current):
    return dict(run=current['run'], response=current['response'], entry_sha=digest(current['entry']))


def validate(db, token, captures, current, packet=None):
    from .evidence import validate_revision
    try:
        validate_revision(captures, current, packet)
    except ValueError:
        receipt = retained(db, token)
        if receipt is None:
            raise
        verify(db, receipt, captures, current, packet)


def verify(db, receipt, captures, current, packet=None):
    if receipt['selection'] != selection(current):
        raise ValueError('article qualification belongs to a different collection receipt')
    row = db.execute('SELECT fetched FROM responses WHERE run=? AND number=?', (current['run'], current['response'])).fetchone()
    fetched = receipt['fetched']
    if receipt['status'] != 200 or not isinstance(fetched, (int, float)) or not row['fetched'] <= fetched <= time.time():
        raise ValueError('article qualification requires successful detail acquired after the collection')
    article_currentness.verify(captures, current, blobs.read(db, receipt['body_sha']), receipt['source'],
                               lambda sha: blobs.read(db, sha), packet)
