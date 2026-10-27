"""Quoted-post provenance ignores handle case while literal claims remain bound."""
from .revisions import revision
from .source_evidence import branch
from .source_links import normalize_quote_link, handle_case_url


def reference_quotes(entries, current, quotes, packet):
    fresh = revision(current)['tweet']
    aliases = set()
    for entry in entries.values():
        old = revision(entry)['tweet']
        for left, right in zip((old, branch(old, 'quoted_status_result', 'result')),
                               (fresh, branch(fresh, 'quoted_status_result', 'result'))):
            aliases.add(canonical_alias(left, right))
    literal = '\n'.join(claim.get('text', '') for claim in (packet or {}).get('claims', ()))
    aliases.difference_update(filter(literal.__contains__, quotes))
    return tuple(quote for quote in quotes if quote not in aliases)


def canonical_alias(old, new):
    old, new = old.get('tweet', old), new.get('tweet', new)
    current = branch(new, 'legacy')
    target = current.get('quoted_status_id_str')
    canonical = 'https://x.com/i/status/' + str(target)
    link = branch(old, 'legacy', 'quoted_status_permalink')
    original = link.get('expanded')
    destination = branch(current, 'quoted_status_permalink').get('expanded')
    equivalent = handle_case_url(destination) == handle_case_url(original)
    if not isinstance(target, str) or not target.isdecimal() or branch(old, 'legacy').get('quoted_status_id_str') != target or not equivalent:
        return None
    normalize_quote_link(old, ())
    return original if link.get('expanded') == canonical and original != canonical else None
