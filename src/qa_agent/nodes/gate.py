"""The human gate.

Deliberately minimal: the node body before interrupt() re-executes on every
resume (documented LangGraph behavior), so it must be pure — build payload,
interrupt, map the resume value into state. Side effects live in `post`, which
only runs after an explicit approve.
"""

from langgraph.types import interrupt


def human_gate(state: dict) -> dict:
    answer = interrupt(
        {
            "ticket_id": state["ticket_id"],
            "overall": state["overall"],
            "verdict": state["verdict"],
            "consulted": state.get("consulted", []),
            "attempts": state["attempts"],
        }
    )
    decision = answer["decision"]
    if decision not in ("approve", "revise", "abort"):
        raise ValueError(f"invalid decision {decision!r}: expected approve|revise|abort")
    update: dict = {"decision": decision}
    if decision == "revise" and answer.get("notes"):
        update["review_notes"] = [answer["notes"]]
    return update
