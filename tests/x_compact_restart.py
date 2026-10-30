"""Fresh-process readback must work without optional memos or native transcripts."""
from pathlib import Path
from contextlib import closing
import sqlite3
import sys
from unittest.mock import patch

from x_curator.publication_audit import verify_publication
from x_curator.wiki_admission import accepted_mapping


def main(root):
    with closing(sqlite3.connect((root / 'curator.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        with patch('x_curator.model_trace.native', side_effect=AssertionError('native replay after restart')):
            for row in db.execute("SELECT * FROM publications WHERE state='published'"):
                verify_publication(db, root, row)
            for row in db.execute("SELECT id FROM wiki_runs WHERE state='accepted'"):
                accepted_mapping(db, row['id'], ())
    print('fresh-process compact verification passed')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
