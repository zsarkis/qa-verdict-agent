"""Run the LangSmith experiment against the review step.

Target = the production review node (same factory the graph uses), fed dataset
inputs. Three evaluators:
  1. overall_exact — exact match on the overall verdict
  2. ac_accuracy   — fraction of per-AC statuses matching the reference
  3. reasoning_quality — LLM-as-judge (openevals), CROSS-FAMILY: the judge
     model (QA_JUDGE_MODEL, GPT) scores the review model's (Claude) reasoning,
     so the system never grades its own homework.

Run with QA_REVIEW_MODE=single vs =tool (default) to compare experiments —
QA-105 is the designed delta (unverifiable from the diff alone; the tool mode
reads app/notifications.py and resolves it).
"""

import os

from langsmith import Client
from openevals.llm import create_llm_as_judge

from evals.dataset import DATASET_NAME
from qa_agent.nodes import make_review
from qa_agent.ports.repo import FixtureRepo
from qa_agent.settings import JUDGE_MODEL, REPO_DIR

review = make_review(FixtureRepo(REPO_DIR))


def target(inputs: dict) -> dict:
    state = {
        "ticket_id": inputs["ticket"]["id"],
        "ticket": inputs["ticket"],
        "context": inputs["context"],
        "diff": inputs["diff"],
        "review_notes": [],
        "attempts": 0,
    }
    update = review(state)
    return {
        "overall": update["overall"],
        "ac_statuses": {r["ac_id"]: r["status"] for r in update["verdict"]["ac_results"]},
        "ac_results": update["verdict"]["ac_results"],
        "summary": update["verdict"]["summary"],
        "consulted": update["consulted"],
    }


def overall_exact(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "overall_exact", "score": outputs["overall"] == reference_outputs["overall"]}


def ac_accuracy(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    reference = reference_outputs["ac_statuses"]
    got = outputs.get("ac_statuses", {})
    correct = sum(got.get(ac_id) == status for ac_id, status in reference.items())
    return {"key": "ac_accuracy", "score": correct / len(reference)}


JUDGE_PROMPT = """You are grading the REASONING QUALITY of a QA verdict produced by an AI \
reviewer, not whether its statuses match the reference (that is scored separately).

<inputs>{inputs}</inputs>
<outputs>{outputs}</outputs>
<reference_outputs>{reference_outputs}</reference_outputs>

The reviewer may have read repository files beyond the diff; outputs.consulted lists them.
Treat citations to those files as legitimately grounded even though their contents are not
shown to you — your grounding check applies to material you CAN see (the diff and context).

Score true only if ALL of the following hold for the outputs:
- Every AC's reasoning is grounded in the diff, the context, or a consulted file — no \
invented behavior attributed to material you can see.
- Evidence citations point at real, relevant locations.
- "unclear" statuses name the specific missing information rather than hedging vaguely.
- The summary is consistent with the per-AC results and actionable for a PM.
"""

reasoning_quality = create_llm_as_judge(
    prompt=JUDGE_PROMPT,
    feedback_key="reasoning_quality",
    model=JUDGE_MODEL,
)


def main() -> None:
    mode = os.environ.get("QA_REVIEW_MODE", "tool")
    client = Client()
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[overall_exact, ac_accuracy, reasoning_quality],
        experiment_prefix=f"review-{mode}",
        metadata={"review_mode": mode},
        max_concurrency=4,
    )
    print(f"experiment: {results.experiment_name}")


if __name__ == "__main__":
    main()
