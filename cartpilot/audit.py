"""Append-only structured audit trail.

Every tool call, decision, and guardrail outcome is logged here so a human can
reconstruct exactly why the agent did what it did. This is the explainability
layer required by the "every money action must be explainable, bounded, and
gated" bar.
"""
import json
import os
import time
import uuid

_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit_log.jsonl")


def log_event(event_type: str, detail: dict, session_id: str) -> dict:
    """Write one structured audit event and return it."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": session_id,
        "event_type": event_type,  # e.g. "tool_call", "guardrail_block", "payment_result"
        "detail": detail,
    }
    with open(_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def new_session_id() -> str:
    return uuid.uuid4().hex[:8]


def read_session(session_id: str) -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    events = []
    with open(_LOG_PATH, "r") as f:
        for line in f:
            entry = json.loads(line)
            if entry["session_id"] == session_id:
                events.append(entry)
    return events
