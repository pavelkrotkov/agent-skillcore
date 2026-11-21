"""Validate executor completion independently of model-authored packet fields."""
from collections import defaultdict
import json

from .model_trace import native, records
from .worker_errors import ModelCompletionError


def framing(log):
    """Check raw JSON framing without interpreting verdicts or controller proof fields."""
    try:
        return records(log)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelCompletionError("malformed model execution", log) from exc


def result(log):
    framing(log)
    # Nested rollout/input proof validation must retain its original rejection type.
    return completed_turn(native(log))


def completed_turn(events):
    # Keep rollout verification in native() outside this conversion.
    # Only completion structure and final JSON errors receive this retryable type.
    try:
        if not events or events[-1]["type"] != "turn.completed":
            raise ModelCompletionError("incomplete model execution")
        return completed(events)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ModelCompletionError("malformed model completion") from exc


def completed(events):
    groups = defaultdict(list)
    for event in events:
        groups[event["type"]].append(event)
    sessions = groups["thread.started"]
    items = [event["item"] for event in groups["item.completed"]]
    messages = [item["text"] for item in items if item["type"] == "agent_message"]
    if len(sessions) != 1 or not messages:
        raise ModelCompletionError("unidentified model execution")
    return sessions[0]["thread_id"], json.loads(messages[-1])
