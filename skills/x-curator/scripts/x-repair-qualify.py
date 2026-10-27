"""Operator-only qualification: one replacement per frozen item, no queue sweep."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from repair_dispatch import run
from repair_qualification import prepare
from x_curator.command_lock import lockfile
from x_curator.storage import open_store
from x_curator.transport import XClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--apply', help='exact digest returned by a fresh preview; run only this manifest')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if args.apply is None:
        path = (args.state / 'curator.sqlite3').resolve()
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            db.row_factory = sqlite3.Row
            result = prepare(db, manifest)
    else:
        with lockfile(args.state, '.collector.lock'), lockfile(args.state, '.repair-qualification.lock'), closing(open_store(args.state)) as db:
            client = XClient()
            try:
                result = run(db, args.state, client, manifest, args.apply)
            finally:
                client.close()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
