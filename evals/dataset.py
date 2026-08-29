"""Build and push the LangSmith eval dataset.

The unit under eval is the review step. Example inputs are built by running the
SAME node functions production uses (intake → retrieve → fetch_diff over each
fixture) — no eval-only reimplementation to drift. Reference outputs come from
data/expected/verdicts.json, which agent nodes never read.

Idempotency: fixture-scale, so delete-and-recreate on every push — the dataset
always mirrors the fixtures exactly.
"""

import json

from langsmith import Client

from qa_agent.nodes import make_fetch_diff, make_intake, make_retrieve
from qa_agent.ports.board import FileBoard
from qa_agent.ports.diffs import FixtureDiffs
from qa_agent.rag import build_retriever
from qa_agent.settings import DIFFS_DIR, EXPECTED_VERDICTS, OUTBOX_DIR, TICKETS_DIR

DATASET_NAME = "qa-verdict-review"


def build_examples() -> list[dict]:
    intake = make_intake(FileBoard(TICKETS_DIR, OUTBOX_DIR))
    retrieve = make_retrieve(build_retriever())
    fetch_diff = make_fetch_diff(FixtureDiffs(DIFFS_DIR))
    expected = json.loads(EXPECTED_VERDICTS.read_text())

    examples = []
    for ticket_id in sorted(k for k in expected if not k.startswith("_")):
        state: dict = {"ticket_id": ticket_id}
        state.update(intake(state))
        if state.get("error"):
            raise RuntimeError(f"fixture {ticket_id} failed intake: {state['error']}")
        state.update(retrieve(state))
        state.update(fetch_diff(state))
        examples.append(
            {
                "inputs": {
                    "ticket": state["ticket"],
                    "context": state["context"],
                    "diff": state["diff"],
                },
                "outputs": {
                    "overall": expected[ticket_id]["overall"],
                    "ac_statuses": expected[ticket_id]["ac_statuses"],
                },
                "metadata": {"ticket_id": ticket_id},
            }
        )
    return examples


def main() -> None:
    client = Client()
    if client.has_dataset(dataset_name=DATASET_NAME):
        client.delete_dataset(dataset_name=DATASET_NAME)
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="QA verdict review step: fixture tickets with expected per-AC statuses",
    )
    examples = build_examples()
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"pushed {len(examples)} examples to dataset {DATASET_NAME!r}")


if __name__ == "__main__":
    main()
