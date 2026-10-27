"""Validate executor completion independently of model-authored packet fields."""
from collections import defaultdict
import json

from .model_trace import native


def result(log):
    events = native(log)
    if not events or events[-1]["type"] != "turn.completed":
        raise ValueError("incomplete model execution")
    return completed(events)


def completed(events):
    groups = defaultdict(list)
    for event in events:
        groups[event["type"]].append(event)
    sessions = groups["thread.started"]
    items = [event["item"] for event in groups["item.completed"]]
    messages = [item["text"] for item in items if item["type"] == "agent_message"]
    if len(sessions) != 1 or not messages:
        raise ValueError("unidentified model execution")
    return sessions[0]["thread_id"], json.loads(messages[-1])
