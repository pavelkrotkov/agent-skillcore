"""Native monotonic markers cannot be rewound independently of their source rows."""
GUARDS = {
 'proof_rows_delete': "CREATE TRIGGER proof_rows_delete BEFORE DELETE ON proof_rows BEGIN SELECT RAISE(ABORT,'proof revisions are append only'); END",
 'proof_rows_insert': "CREATE TRIGGER proof_rows_insert BEFORE INSERT ON proof_rows WHEN EXISTS(SELECT 1 FROM proof_rows WHERE table_name=NEW.table_name AND row_id=NEW.row_id) BEGIN SELECT RAISE(ABORT,'proof revisions cannot be replaced'); END",
 'proof_rows_update': "CREATE TRIGGER proof_rows_update BEFORE UPDATE ON proof_rows WHEN NEW.table_name!=OLD.table_name OR NEW.row_id!=OLD.row_id OR NEW.version<=OLD.version BEGIN SELECT RAISE(ABORT,'proof revisions cannot be rewound'); END",
}


def changes(table):
    for event in ('insert','update','delete'):
        row='OLD' if event=='delete' else 'NEW'
        key=f"table_name='{table}' AND row_id={row}.rowid"
        name=f'proof_{table}_{event}'
        yield name, (f'CREATE TRIGGER {name} AFTER {event.upper()} ON "{table}" BEGIN '
            f'UPDATE proof_rows SET version=version+1 WHERE {key}; '
            f"INSERT INTO proof_rows SELECT '{table}',{row}.rowid,1 WHERE NOT EXISTS(SELECT 1 FROM proof_rows WHERE {key}); END")


def require(expected, actual):
    if any(actual.get(name)!=sql for name,sql in expected.items()):
        raise ValueError('proof revision infrastructure changed; explicit repair required')


def initialize(db):
    existing=db.execute("SELECT 1 FROM sqlite_master WHERE name='proof_rows'").fetchone()
    db.execute('CREATE TABLE IF NOT EXISTS proof_rows(table_name TEXT,row_id INTEGER,version INTEGER NOT NULL CHECK(typeof(version)=\'integer\' AND version>0),PRIMARY KEY(table_name,row_id)) WITHOUT ROWID')
    db.execute('CREATE TABLE IF NOT EXISTS proof_tables(name TEXT PRIMARY KEY)')
    actual=dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    if existing:
        require(GUARDS,actual)
    for name,sql in GUARDS.items():
        if name not in actual:
            db.execute(sql)
            actual[name]=sql
    require(GUARDS,actual)
    return actual

def initialize_table(db,table,actual):
    expected=dict(changes(table))
    if db.execute('SELECT 1 FROM proof_tables WHERE name=?',(table,)).fetchone():
        require(expected,actual)
        return
    for sql in expected.values():
        db.execute(sql)
    db.execute(f"INSERT INTO proof_rows SELECT '{table}',rowid,1 FROM \"{table}\"")
    db.execute('INSERT INTO proof_tables VALUES (?)',(table,))
