"""Graph state for a QA episode.

Design constraints (see DECISIONS.md §3):
- Everything JSON-serializable: no message objects, no custom classes. The
  SQLite checkpointer serializes state as-is, and a checkpoint dump stays
  human-readable.
- No `confidence` float: the LLM makes per-AC judgments only; `overall` is
  computed in code (see verdict.compute_overall).
- No top-level `messages` channel: this is a workflow graph, not a chat agent.
  The review node's tool loop keeps its messages internal.
- `review_notes` accumulates across revise loops (operator.add); everything
  else is last-value. The parallel branch (retrieve / fetch_diff) writes
  disjoint keys, so no other reducers are needed.
"""

import operator
from typing import Annotated, Literal

from typing_extensions import TypedDict


class ACResult(TypedDict):
    ac_id: str
    status: Literal["pass", "fail", "unclear"]
    reasoning: str
    evidence: list[str]


class Verdict(TypedDict):
    ac_results: list[ACResult]
    summary: str


class EpisodeState(TypedDict):
    # input
    ticket_id: str
    # intake (redacted BEFORE entering state — PII never reaches a checkpoint)
    ticket: dict | None
    redaction_log: list[str]
    # gathered context (parallel branch — disjoint keys)
    context: list[dict]
    diff: str | None
    # judgment
    verdict: Verdict | None
    overall: Literal["pass", "fail", "needs_info"] | None
    consulted: list[str]  # files the review read beyond the diff (audit trail)
    review_notes: Annotated[list[str], operator.add]
    attempts: int
    # gate + outcome
    decision: Literal["approve", "revise", "abort"] | None
    post_result: dict | None
    error: str | None
