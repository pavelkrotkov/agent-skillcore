"""Validate response envelopes and extract selected timeline entries."""
import json

from .entries import selection, timeline_entries

def instructions(body, kind):
    """Require a recognized account timeline, not just a successful HTTP status."""
    payload = json.loads(body)
    if payload.get("errors"):
        raise ValueError("X returned GraphQL errors")
    if kind == "likes":
        result = payload["data"]["user"]["result"]
        container = result.get("timeline") or result["timeline_v2"]
    else:
        container = payload["data"]["bookmark_timeline_v2"]
    values = container["timeline"]["instructions"]
    if not isinstance(values, list) or not values:
        raise ValueError("missing timeline instructions")
    return values


def parse(body, kind):
    # Keep known selected IDs from partial pages without permitting checkpoint advancement.
    entries, terminal, page, errors = timeline_entries(instructions(body, kind))
    items, cursor, entry_errors = parse_entries(entries)
    errors.extend(entry_errors)
    if not page:
        errors.append("no recognized page or end instruction")
    return items, None if terminal else cursor, "; ".join(errors) or None


def parse_entries(entries):
    items = []
    cursor = None
    errors = []
    for entry in entries:
        try:
            item, next_cursor = parse_entry(entry)
            if item:
                items.append(item)
            if next_cursor is not None:
                cursor = next_cursor
        except (ValueError, KeyError, TypeError, AttributeError):
            errors.append("unsupported or malformed timeline entry")
    if any(item[1] == "malformed" for item in items):
        errors.append("malformed selected source")
    return items, cursor, errors


def parse_entry(entry):
    entry_id = entry["entryId"]
    if entry_id.startswith("tweet-"):
        return selection(entry), None
    if entry_id.startswith("cursor-bottom-"):
        cursor = entry["content"]["value"]
        validate_cursor(cursor)
        return None, cursor
    if entry_id.startswith("cursor-top-"):
        return None, None
    raise ValueError("unsupported timeline entry")


def validate_cursor(cursor):
    if not isinstance(cursor, str) or not cursor:
        raise ValueError("invalid pagination cursor")
