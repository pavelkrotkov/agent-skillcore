"""Only simple complete row sets qualify for thin revision projections."""
from functools import lru_cache
import re


@lru_cache(maxsize=1024)
def projection(sql, tables):
    match=re.fullmatch(r'\s*SELECT\s+([\w*,\s]+?)\s+FROM\s+(\w+)(\s+(?:WHERE|ORDER BY)\b.*|\s*)',sql,re.I|re.S)
    if match is None or match[2] not in tables:
        return None
    if re.search(r'\b(SELECT|JOIN|LIMIT|GROUP|HAVING|UNION|EXCEPT|INTERSECT|DISTINCT|OFFSET)\b',match[1]+match[3],re.I):
        return None
    if not re.fullmatch(r'(?:\*|\w+)(?:\s*,\s*\w+)*',match[1].strip()):
        return None
    table,tail=match[2],match[3]
    return (f'SELECT "{table}".rowid,(SELECT version FROM proof_rows '
            f"WHERE table_name='{table}' AND row_id=\"{table}\".rowid) FROM \"{table}\""+tail)
