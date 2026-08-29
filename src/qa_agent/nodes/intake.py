"""Intake: load the card, normalize ACs, redact PII — all before anything
enters state, so raw ticket text never reaches the checkpoint DB, the LLM,
or LangSmith traces.

Error taxonomy (DECISIONS.md §16): expected business failures (unknown ticket,
wrong status, no ACs) set state["error"] and route to END; broken fixtures and
infra errors raise and fail the run loudly — the checkpoint preserves progress
and the run is resumable after the fix.
"""

from collections import Counter

from qa_agent.ports.board import TicketBoard
from qa_agent.redact import redact


def _merge_logs(*logs: list[str]) -> list[str]:
    counts: Counter = Counter()
    for log in logs:
        for entry in log:
            label, _, n = entry.partition(":")
            counts[label] += int(n)
    return [f"{label}:{n}" for label, n in sorted(counts.items())]


def make_intake(board: TicketBoard):
    def intake(state: dict) -> dict:
        try:
            raw = board.get_ticket(state["ticket_id"])
        except KeyError as exc:
            return {"error": str(exc)}

        if raw.get("status") != "ready_for_qa":
            return {"error": f"ticket {raw['id']} has status {raw.get('status')!r}, not 'ready_for_qa'"}
        if not raw.get("acceptance_criteria"):
            return {"error": f"ticket {raw['id']} has no acceptance criteria to review against"}
        if not raw.get("diff_ref"):
            return {"error": f"ticket {raw['id']} names no diff to review (missing diff_ref)"}

        title, title_log = redact(raw.get("title", ""))
        body, body_log = redact(raw.get("body", ""))
        ac_logs = []
        criteria = []
        for ac in raw["acceptance_criteria"]:
            text, log = redact(ac["text"])
            criteria.append({"id": ac["id"], "text": text})
            ac_logs.append(log)

        ticket = {
            "id": raw["id"],
            "title": title,
            "type": raw.get("type", "unknown"),
            "body": body,
            "acceptance_criteria": criteria,
            "diff_ref": raw["diff_ref"],
        }
        return {"ticket": ticket, "redaction_log": _merge_logs(title_log, body_log, *ac_logs)}

    return intake
