"""Interpret selected entries and timeline control instructions."""
import re

def selection(entry):
    """Keep tombstone IDs: inaccessible sources remain owned work."""
    source_id = entry["entryId"][6:]
    if not re.fullmatch(r"[0-9]+", source_id):
        raise ValueError("invalid selected source identity")
    return source_id, availability(entry, source_id), entry


def availability(entry, source_id):
    # Only explicit tombstones prove unavailability; parser drift must remain distinguishable.
    try:
        tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
        original = tweet.get("tweet", tweet)
        kind = original.get("__typename", tweet["__typename"])
        if kind in ("TweetUnavailable", "TweetTombstone"):
            return "unavailable"
        if kind in ("Tweet", "TweetWithVisibilityResults") and original["rest_id"] == source_id:
            return "available"
    except (KeyError, TypeError, AttributeError):
        pass
    return "malformed"


def timeline_entries(values):
    """Unknown structures stop the pass rather than silently dropping selections."""
    entries = []
    terminal, page = False, False
    errors = []
    for instruction in values:
        try:
            chunk, end, valid_page = instruction_entries(instruction)
            entries.extend(chunk)
            terminal |= end
            page |= valid_page
        except (ValueError, KeyError, TypeError, AttributeError):
            errors.append("unsupported or malformed timeline instruction")
    return entries, terminal, page or terminal, errors


def instruction_entries(instruction):
    kind = instruction["type"]
    if kind == "TimelineAddEntries":
        entries = instruction["entries"]
        if not isinstance(entries, list):
            raise ValueError("entries must be a list")
        return entries, False, True
    if kind == "TimelinePinEntry":
        return [instruction["entry"]], False, False
    if kind == "TimelineTerminateTimeline":
        return [], instruction.get("direction") == "Bottom", False
    if kind == "TimelineClearCache":
        return [], False, False
    raise ValueError("unknown instruction")
