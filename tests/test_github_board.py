"""GitHubBoard tests — parser and adapter behavior, no network (fake transport)."""

import pytest

from qa_agent.ports.github_board import (
    GitHubBoard,
    parse_issue_body,
    render_verdict_comment,
)

BODY = """Sales wants a volume incentive for bulk orders.

## Acceptance Criteria
- [ ] AC-1: Orders with 5 or more total items get a 10% discount
- [ ] AC-2: The discounted subtotal is a correctly rounded currency value

Diff-Ref: QA-103.diff
"""


class FakeTransport:
    def __init__(self, issue, listing=None):
        self.issue = issue
        self.listing = listing or []
        self.posted = []

    def get(self, path):
        if "labels=" in path:
            return self.listing
        return self.issue

    def post(self, path, payload):
        self.posted.append((path, payload))
        return {"html_url": "https://github.com/o/r/issues/7#issuecomment-1"}


def make_issue(**overrides):
    issue = {
        "number": 7,
        "title": "Bulk discount for orders of 5+ items",
        "body": BODY,
        "labels": [{"name": "ready-for-qa"}],
    }
    issue.update(overrides)
    return issue


def test_parse_extracts_acs_and_diff_ref():
    description, criteria, diff_ref = parse_issue_body(BODY)
    assert "volume incentive" in description
    assert "Diff-Ref" not in description
    assert [ac["id"] for ac in criteria] == ["AC-1", "AC-2"]
    assert criteria[1]["text"].startswith("The discounted subtotal")
    assert diff_ref == "QA-103.diff"


def test_parse_autonumbers_unlabeled_criteria():
    _, criteria, _ = parse_issue_body("## Acceptance Criteria\n- [ ] first\n- [x] second")
    assert [ac["id"] for ac in criteria] == ["AC-1", "AC-2"]
    assert criteria[1]["text"] == "second"


def test_parse_handles_missing_sections():
    description, criteria, diff_ref = parse_issue_body("just prose, no structure")
    assert criteria == []
    assert diff_ref is None
    assert description == "just prose, no structure"


def test_get_ticket_maps_issue_to_ticket_contract():
    board = GitHubBoard("o/r", transport=FakeTransport(make_issue()))
    ticket = board.get_ticket("7")
    assert ticket["id"] == "7"
    assert ticket["status"] == "ready_for_qa"
    assert ticket["diff_ref"] == "QA-103.diff"
    assert len(ticket["acceptance_criteria"]) == 2


def test_missing_label_is_a_business_status_not_an_exception():
    board = GitHubBoard("o/r", transport=FakeTransport(make_issue(labels=[])))
    assert board.get_ticket("7")["status"] != "ready_for_qa"


def test_non_numeric_ticket_id_rejected():
    board = GitHubBoard("o/r", transport=FakeTransport(make_issue()))
    with pytest.raises(KeyError):
        board.get_ticket("QA-101")


def test_post_verdict_comments_on_the_issue():
    transport = FakeTransport(make_issue())
    board = GitHubBoard("o/r", transport=transport)
    result = board.post_verdict("7", {
        "overall": "fail",
        "ac_results": [
            {"ac_id": "AC-1", "status": "pass", "reasoning": "ok", "evidence": ["app/orders.py"]},
            {"ac_id": "AC-2", "status": "fail", "reasoning": "truncation", "evidence": []},
        ],
        "summary": "Truncation defect.",
        "attempts": 1,
        "consulted": ["app/orders.py"],
        "redaction_log": [],
    })
    assert result["posted"] is True
    assert "issuecomment" in result["location"]
    path, payload = transport.posted[0]
    assert path == "/repos/o/r/issues/7/comments"
    assert "QA Verdict" in payload["body"]
    assert "AC-2" in payload["body"]


def test_list_ready_returns_issue_numbers_and_skips_prs():
    listing = [
        {"number": 7},
        {"number": 9, "pull_request": {"url": "..."}},  # PRs come back from the issues endpoint
        {"number": 12},
    ]
    board = GitHubBoard("o/r", transport=FakeTransport(make_issue(), listing=listing))
    assert board.list_ready() == ["7", "12"]


def test_comment_renders_audit_footer():
    body = render_verdict_comment({
        "overall": "pass",
        "ac_results": [{"ac_id": "AC-1", "status": "pass", "reasoning": "ok", "evidence": []}],
        "summary": "s",
        "attempts": 2,
        "consulted": ["app/notifications.py"],
        "redaction_log": ["EMAIL:1"],
    })
    assert "review attempt 2" in body
    assert "app/notifications.py" in body
    assert "EMAIL:1" in body
    assert "human approval" in body
