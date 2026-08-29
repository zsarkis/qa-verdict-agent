from langgraph.graph import END

from qa_agent.graph import route_after_gate, route_after_intake
from qa_agent.nodes import make_intake
from qa_agent.ports.board import FileBoard
from qa_agent.settings import TICKETS_DIR


def intake(ticket_id, tmp_path):
    node = make_intake(FileBoard(TICKETS_DIR, tmp_path))
    return node({"ticket_id": ticket_id})


def test_intake_normalizes_clean_ticket(tmp_path):
    update = intake("QA-101", tmp_path)
    assert "error" not in update
    ticket = update["ticket"]
    assert ticket["id"] == "QA-101"
    assert [ac["id"] for ac in ticket["acceptance_criteria"]] == ["AC-1", "AC-2", "AC-3"]
    assert update["redaction_log"] == []


def test_intake_redacts_pii_before_state(tmp_path):
    update = intake("QA-108", tmp_path)
    body = update["ticket"]["body"]
    for pii in ("acmemail.com", "555-867-5309", "4111"):
        assert pii not in body
    assert update["redaction_log"] == ["CARD:1", "EMAIL:1", "PHONE:1"]


def test_intake_unknown_ticket_sets_error(tmp_path):
    update = intake("QA-999", tmp_path)
    assert "QA-999" in update["error"]
    assert "ticket" not in update


def test_route_after_intake():
    assert route_after_intake({"error": "boom"}) == END
    assert route_after_intake({"error": None}) == ["retrieve", "fetch_diff"]
    assert route_after_intake({}) == ["retrieve", "fetch_diff"]


def test_route_after_gate():
    assert route_after_gate({"decision": "approve"}) == "post"
    assert route_after_gate({"decision": "revise"}) == "review"
    assert route_after_gate({"decision": "abort"}) == END
