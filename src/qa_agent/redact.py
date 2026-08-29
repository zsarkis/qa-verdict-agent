"""Deterministic PII redaction.

Regex-based on purpose: a guardrail should not depend on the model it guards.
Called inside the intake node BEFORE ticket text enters graph state, so raw PII
never reaches the checkpoint DB, the LLM, or LangSmith traces. Production path
would be Microsoft Presidio behind this same function signature.

Known limitation (documented, acceptable here): free-text person names are not
redacted — reliable name detection needs NER, which is Presidio territory.
"""

import re

# Order matters: cards before phones so a 16-digit number is never half-eaten
# by the phone pattern.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("CARD", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s])?(?:\(\d{3}\)\s?|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b")),
]


def redact(text: str) -> tuple[str, list[str]]:
    """Scrub PII from text.

    Returns (scrubbed_text, log) where log entries are "TYPE:count" — the types
    of what was removed, never the values.
    """
    log: list[str] = []
    for label, pattern in PATTERNS:
        text, count = pattern.subn(f"[REDACTED:{label}]", text)
        if count:
            log.append(f"{label}:{count}")
    return text, log
