"""The review node — the one place in the graph with model agency, bounded.

Two modes via QA_REVIEW_MODE (default "tool"):
- "single": one structured-output call, a pure function of state.
- "tool":   the model may call get_file_context up to TOOL_BUDGET times to read
            repository files outside the diff, then must produce the verdict.

The budget is enforced INSIDE the tool (an over-budget call returns a "judge
with what you have" message) rather than via recursion_limit, which would abort
the run instead of forcing a graceful verdict. The system prompt carries only
the FORM contract (statuses, evidence, honesty about unverifiability); the
team's judgment standards (money rules, boundary literalism, regression policy)
come from the retrieved KB context — knowledge lives in the KB, orchestration
in code, not prompts.

`overall` is computed in code after the LLM returns; coverage is enforced by
normalize_results (skipped ACs become unclear, hallucinated AC ids dropped).
"""

import os
from typing import Literal

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from qa_agent.ports.repo import RepoSource
from qa_agent.settings import REVIEW_MODEL
from qa_agent.verdict import compute_overall, normalize_results

TOOL_BUDGET = 2


class ACResultModel(BaseModel):
    ac_id: str = Field(description="The acceptance criterion id, e.g. 'AC-1'")
    status: Literal["pass", "fail", "unclear"]
    reasoning: str = Field(description="One to three sentences grounded in cited evidence")
    evidence: list[str] = Field(
        description="Diff hunks or file references supporting the status, e.g. 'app/orders.py: shipping_fee'"
    )


class VerdictModel(BaseModel):
    ac_results: list[ACResultModel]
    summary: str = Field(description="Two to three sentences a non-engineer PM can act on")


SYSTEM = """You are a QA reviewer. Judge a code diff against a ticket's acceptance criteria.

Rules of form:
- Judge ONLY the listed acceptance criteria, each by its id. Address every one.
- Status per AC: "pass" (verifiably met), "fail" (verifiably not met, including \
regressions the AC protects against), "unclear" (cannot be confirmed or denied from the \
available material). Never guess: unverifiable means unclear, not pass.
- Cite evidence (file and function/hunk) for every pass and fail.
- Apply the team's documented standards from the provided TEAM CONTEXT when an AC uses \
judgment words like "correctly"; the context defines what the team means by them. Standards \
INTERPRET the listed ACs — they never add new criteria beyond them. Improvements you'd like \
that no AC requires belong in the summary as advisory notes, not in a status.
- The diff is responsible for what it removes, not just what it adds — when an AC protects \
existing behavior.
- Each reasoning is at most three sentences, and the status must match the reasoning's own \
conclusion.
- Code cannot define business policy. If an AC depends on a value or policy (a cutoff, a \
rate, a rule) that no ticket text or team document defines, that AC is unclear no matter \
what the implementation hardcodes — reading more code cannot resolve it.
- Judge the diff, not the surrounding codebase: a pre-existing defect in code the diff \
does not touch is an advisory note for the summary, not an AC failure — unless an AC \
explicitly protects that behavior."""

SYSTEM_TOOL = SYSTEM + f"""

You may call get_file_context(path) up to {TOOL_BUDGET} times to read repository files that the
diff touches or references, when an AC cannot be verified from the diff alone. Then produce
the verdict."""


def _build_user_prompt(state: dict) -> str:
    ticket = state["ticket"]
    acs = "\n".join(f'- {ac["id"]}: {ac["text"]}' for ac in ticket["acceptance_criteria"])
    context = "\n\n".join(
        f'[source: {c["source"]}]\n{c["text"]}' for c in state.get("context", [])
    )
    parts = [
        f"TICKET {ticket['id']} ({ticket['type']}): {ticket['title']}",
        f"DESCRIPTION:\n{ticket['body']}",
        f"ACCEPTANCE CRITERIA:\n{acs}",
        f"TEAM CONTEXT:\n{context}",
        f"DIFF:\n{state['diff']}",
    ]
    notes = [n for n in state.get("review_notes", []) if n]
    if notes:
        parts.append(
            "HUMAN REVISION NOTES (a reviewer rejected a previous draft; address these):\n"
            + "\n".join(f"- {n}" for n in notes)
        )
    return "\n\n".join(parts)


def make_review(repo: RepoSource):
    # The (state, config) signature lets us thread the graph's RunnableConfig
    # into the inner model/agent invocations: that is what nests their spans
    # under this node in traces AND propagates the callbacks that
    # stream_mode="messages" rides on. Without it, tool calls are invisible to
    # the CLI stream.
    def review(state: dict, config=None) -> dict:
        mode = os.environ.get("QA_REVIEW_MODE", "tool")
        model = init_chat_model(REVIEW_MODEL, temperature=0)
        user_prompt = _build_user_prompt(state)

        consulted: list[str] = []
        if mode == "single":
            structured = model.with_structured_output(VerdictModel)
            result = structured.invoke(
                [SystemMessage(content=SYSTEM), HumanMessage(content=user_prompt)],
                config=config,
            )
        else:
            calls = {"n": 0}

            @tool
            def get_file_context(path: str) -> str:
                """Read a repository file outside the diff, e.g. 'app/notifications.py'.
                Use when an acceptance criterion cannot be verified from the diff alone."""
                if calls["n"] >= TOOL_BUDGET:
                    return (
                        "Tool budget exhausted. Judge with the information you have; "
                        "mark ACs you cannot verify as unclear."
                    )
                calls["n"] += 1
                try:
                    content = repo.get_file(path)
                except (ValueError, FileNotFoundError) as exc:
                    return f"error: {exc}"
                consulted.append(path)
                return content

            # Built per invocation so the tool budget is scoped to this episode's
            # review attempt; construction is local graph wiring, no API calls.
            agent = create_agent(
                model=model,
                tools=[get_file_context],
                system_prompt=SYSTEM_TOOL,
                response_format=VerdictModel,
            )
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_prompt)]}, config=config
            )["structured_response"]

        verdict = result.model_dump()
        ac_ids = [ac["id"] for ac in state["ticket"]["acceptance_criteria"]]
        verdict["ac_results"] = normalize_results(ac_ids, verdict["ac_results"])
        return {
            "verdict": verdict,
            "overall": compute_overall(verdict["ac_results"]),
            "consulted": consulted,
            "attempts": state.get("attempts", 0) + 1,
        }

    return review
