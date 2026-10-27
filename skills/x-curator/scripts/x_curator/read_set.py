"""Fence approval queries and consumed-file bytes without repeating heavy proofs."""
from .row_fingerprint import query_stamp
from .proof_reads import read_file,record_file,stamp_file
from .proof_files import fingerprints


class ChangedDependencies(ValueError):
    pass


class ReadSet:
    def __init__(self, db, shared=False):
        self.db = db
        self.queries = {}
        self.files = {}
        self.shared = shared
        self.metadata = {}
        self.namespace = db.namespace if isinstance(db, ReadSet) else {}

    def execute(self, sql, parameters=()):
        statement = sql.strip().upper()
        if not (statement.startswith('SELECT ') or statement == 'PRAGMA DATABASE_LIST'):
            raise ValueError('approval proof must contain only recorded reads')
        parameters = tuple(parameters)
        self.queries.setdefault((sql, parameters), None)
        return self.db.execute(sql, parameters)

    def fingerprint(self):
        queries = {query: query_stamp(self.db, query) for query in self.queries}
        files,metadata = fingerprints(self)
        # A baseline captured after validation could bless a racing file replacement.
        if files != self.files:
            raise ChangedDependencies('publication files changed during verification')
        self.metadata.update(metadata)
        if isinstance(self.db, ReadSet):
            self.db.queries.update(queries)
        return queries, files

    def captured(self):
        """Retain verified child digests; activation must still call fresh verify()."""
        return ({query: stamp if stamp is not None else query_stamp(self.db,query)
                 for query, stamp in self.queries.items()}, dict(self.files))

    def read_file(self, root, relative):
        return record_file(self,root,relative)

    def verify(self, expected):
        if not isinstance(self.db, ReadSet):
            self.namespace.clear()
        if self.fingerprint() != expected:
            raise ChangedDependencies('publication dependencies changed during verification')

    def query_stamp(self, query):
        if not self.shared or self.queries.get(query) is None:
            self.queries[query] = query_stamp(self.db, query)
        return self.queries[query]

    def file_stamp(self, file, verified=None):
        return stamp_file(self,file,verified)
