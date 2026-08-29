"""Ticket-board port.

The graph talks to a TicketBoard protocol, never to a vendor API. The default
adapter is file-backed so the whole demo runs with zero external services or
keys. A real adapter (Trello, Jira, Linear) implements the same two methods and
swaps in behind a flag — a stretch goal, deliberately last.

Plain dicts at the seam, matching the JSON-serializable-state rule: everything
that crosses into graph state must survive the checkpointer and read cleanly in
a checkpoint dump. Pydantic validation at this boundary is a listed improvement.
"""

import json
from pathlib import Path
from typing import Protocol


class TicketBoard(Protocol):
    def get_ticket(self, ticket_id: str) -> dict: ...

    def post_verdict(self, ticket_id: str, verdict: dict) -> dict: ...

    def list_ready(self) -> list[str]: ...


class FileBoard:
    """File-backed stub: tickets are JSON fixtures, verdicts land in an outbox dir."""

    def __init__(self, tickets_dir: Path, outbox_dir: Path):
        self.tickets_dir = Path(tickets_dir)
        self.outbox_dir = Path(outbox_dir)

    def get_ticket(self, ticket_id: str) -> dict:
        path = self.tickets_dir / f"{ticket_id}.json"
        if not path.is_file():
            known = sorted(p.stem for p in self.tickets_dir.glob("*.json"))
            raise KeyError(f"unknown ticket {ticket_id!r}; known tickets: {known}")
        return json.loads(path.read_text())

    def post_verdict(self, ticket_id: str, verdict: dict) -> dict:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        path = self.outbox_dir / f"{ticket_id}.verdict.json"
        path.write_text(json.dumps(verdict, indent=2) + "\n")
        return {"posted": True, "location": str(path)}

    def list_ready(self) -> list[str]:
        ready = []
        for path in sorted(self.tickets_dir.glob("*.json")):
            if json.loads(path.read_text()).get("status") == "ready_for_qa":
                ready.append(path.stem)
        return ready
