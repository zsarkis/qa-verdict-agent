import pytest

from qa_agent.verdict import compute_overall, normalize_results


def result(ac_id, status):
    return {"ac_id": ac_id, "status": status, "reasoning": "r", "evidence": []}


def test_all_pass():
    assert compute_overall([result("AC-1", "pass"), result("AC-2", "pass")]) == "pass"


def test_any_fail_wins():
    assert compute_overall([result("AC-1", "pass"), result("AC-2", "fail")]) == "fail"


def test_fail_beats_unclear():
    assert (
        compute_overall([result("AC-1", "unclear"), result("AC-2", "fail")]) == "fail"
    )


def test_unclear_means_needs_info():
    assert (
        compute_overall([result("AC-1", "pass"), result("AC-2", "unclear")])
        == "needs_info"
    )


def test_empty_results_raise():
    with pytest.raises(ValueError):
        compute_overall([])


def test_normalize_fills_skipped_acs_as_unclear():
    normalized = normalize_results(["AC-1", "AC-2"], [result("AC-1", "pass")])
    assert [r["ac_id"] for r in normalized] == ["AC-1", "AC-2"]
    assert normalized[1]["status"] == "unclear"


def test_normalize_drops_hallucinated_ac_ids():
    normalized = normalize_results(["AC-1"], [result("AC-1", "pass"), result("AC-9", "fail")])
    assert [r["ac_id"] for r in normalized] == ["AC-1"]


def test_normalize_preserves_ticket_order():
    normalized = normalize_results(
        ["AC-1", "AC-2"], [result("AC-2", "fail"), result("AC-1", "pass")]
    )
    assert [r["ac_id"] for r in normalized] == ["AC-1", "AC-2"]
