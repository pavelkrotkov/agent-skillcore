"""Read authentic model and tool timing without replaying any work."""
import sqlite3

def receipt_rows(db, tokens, table):
    if not tokens:
        return []
    columns = {'executions': 'id,token,role AS name,model,started,finished',
               'quick_tools': 'id,token,name,created AS started,finished'}[table]
    try:
        records = db.execute(f'SELECT {columns} FROM {table} WHERE token IN ({",".join("?" for _ in tokens)}) ORDER BY started,id', tokens)
        return [dict(row, elapsed_seconds=row['finished']-row['started'] if row['finished'] is not None else None,
                     usage=None) for row in records]
    except sqlite3.OperationalError:
        return []
