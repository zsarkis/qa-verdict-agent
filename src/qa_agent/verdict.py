"""Deterministic verdict aggregation.

The LLM produces per-AC judgments; everything that can be code, is code:
coverage enforcement and the overall verdict live here, not in a prompt.
"""

from qa_agent.state import ACResult


def normalize_results(ac_ids: list[str], ac_results: list[ACResult]) -> list[ACResult]:
    """Enforce exactly one result per acceptance criterion.

    An AC the model skipped becomes `unclear` (an unaddressed criterion is by
    definition unverified); results for AC ids the ticket doesn't have are
    dropped. Order follows the ticket's AC order.
    """
    by_id = {r["ac_id"]: r for r in ac_results}
    normalized: list[ACResult] = []
    for ac_id in ac_ids:
        if ac_id in by_id:
            normalized.append(by_id[ac_id])
        else:
            normalized.append(
                {
                    "ac_id": ac_id,
                    "status": "unclear",
                    "reasoning": "Not addressed by the reviewer; treated as unverified.",
                    "evidence": [],
                }
            )
    return normalized


def compute_overall(ac_results: list[ACResult]) -> str:
    """fail > unclear > pass. Any fail fails the ticket; otherwise any unclear
    sends it back for information; otherwise it passes."""
    if not ac_results:
        raise ValueError("cannot compute an overall verdict from zero AC results")
    statuses = {r["status"] for r in ac_results}
    if "fail" in statuses:
        return "fail"
    if "unclear" in statuses:
        return "needs_info"
    return "pass"
