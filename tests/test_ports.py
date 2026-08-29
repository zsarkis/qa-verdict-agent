import json

import pytest

from qa_agent.ports.board import FileBoard
from qa_agent.ports.diffs import FixtureDiffs
from qa_agent.ports.repo import FixtureRepo
from qa_agent.settings import DIFFS_DIR, REPO_DIR, TICKETS_DIR


def test_fileboard_loads_ticket(tmp_path):
    board = FileBoard(TICKETS_DIR, tmp_path)
    ticket = board.get_ticket("QA-101")
    assert ticket["id"] == "QA-101"
    assert ticket["status"] == "ready_for_qa"
    assert {ac["id"] for ac in ticket["acceptance_criteria"]} == {"AC-1", "AC-2", "AC-3"}


def test_fileboard_unknown_ticket_names_known_ones(tmp_path):
    board = FileBoard(TICKETS_DIR, tmp_path)
    with pytest.raises(KeyError, match="QA-101"):
        board.get_ticket("QA-999")


def test_fileboard_posts_to_outbox(tmp_path):
    board = FileBoard(TICKETS_DIR, tmp_path / "outbox")
    result = board.post_verdict("QA-101", {"overall": "pass"})
    assert result["posted"] is True
    posted = json.loads((tmp_path / "outbox" / "QA-101.verdict.json").read_text())
    assert posted == {"overall": "pass"}


def test_fileboard_lists_ready_tickets(tmp_path):
    board = FileBoard(TICKETS_DIR, tmp_path)
    ready = board.list_ready()
    assert "QA-101" in ready and "QA-110" in ready
    assert len(ready) == 10  # every fixture ships ready_for_qa


def test_fixture_diffs_returns_diff_text():
    diffs = FixtureDiffs(DIFFS_DIR)
    diff = diffs.get_diff("QA-109.diff")
    assert "item_count > BULK_FREE_SHIPPING_MIN_ITEMS" in diff


def test_fixture_diffs_unknown_ref():
    diffs = FixtureDiffs(DIFFS_DIR)
    with pytest.raises(KeyError):
        diffs.get_diff("QA-999.diff")


def test_repo_reads_file():
    repo = FixtureRepo(REPO_DIR)
    assert "def order_total" in repo.get_file("app/orders.py")


def test_repo_lists_files():
    repo = FixtureRepo(REPO_DIR)
    assert "app/orders.py" in repo.list_files()


def test_repo_blocks_path_traversal():
    repo = FixtureRepo(REPO_DIR)
    with pytest.raises(ValueError, match="escapes"):
        repo.get_file("../../pyproject.toml")


def test_repo_blocks_absolute_paths():
    repo = FixtureRepo(REPO_DIR)
    with pytest.raises((ValueError, FileNotFoundError)):
        repo.get_file("/etc/hosts")


def test_repo_missing_file_lists_alternatives():
    repo = FixtureRepo(REPO_DIR)
    with pytest.raises(FileNotFoundError, match="app/orders.py"):
        repo.get_file("app/nope.py")
