"""StateGraph wiring — the composition root.

Edge map:
    START -> intake
    intake -> conditional: error set -> END, else fan-out to [retrieve, fetch_diff]
    [retrieve, fetch_diff] -> review        # fan-in: waits for both
    review -> human_gate                     # unconditional; every verdict is gated
    human_gate -> conditional on decision: approve -> post | revise -> review | abort -> END
    post -> END

Routers are dumb on purpose: they read one field a node already wrote and
contain no logic of their own. All ports are injectable; defaults are the
file-backed adapters, so tests swap in fakes and a real board adapter is a
one-line change here.
"""

from langgraph.graph import END, START, StateGraph

from qa_agent.nodes import (
    human_gate,
    make_fetch_diff,
    make_intake,
    make_post,
    make_retrieve,
    make_review,
)
from qa_agent.ports.board import FileBoard
from qa_agent.ports.diffs import FixtureDiffs
from qa_agent.ports.repo import FixtureRepo
from qa_agent.settings import DIFFS_DIR, OUTBOX_DIR, REPO_DIR, TICKETS_DIR
from qa_agent.state import EpisodeState


def route_after_intake(state: dict):
    return END if state.get("error") else ["retrieve", "fetch_diff"]


def route_after_gate(state: dict):
    decision = state["decision"]
    if decision == "approve":
        return "post"
    if decision == "revise":
        return "review"
    return END


def default_board():
    """Composition-root board selection: QA_BOARD=file (default) | github.

    The graph never knows which board it has — that's the whole point of the
    port. The github adapter needs QA_BOARD_REPO ('owner/name') and GITHUB_TOKEN.
    """
    import os

    if os.environ.get("QA_BOARD", "file") == "github":
        from qa_agent.ports.github_board import GitHubBoard

        repo_name = os.environ.get("QA_BOARD_REPO", "")
        if not repo_name:
            raise RuntimeError("QA_BOARD=github requires QA_BOARD_REPO=owner/name")
        return GitHubBoard(repo_name)
    return FileBoard(TICKETS_DIR, OUTBOX_DIR)


def _default_repo():
    """Composition-root repo selection for get_file_context: QA_REPO_DIR points
    the review tool at any checkout (e.g. the real project a live ticket
    belongs to); default is the fixture app. The path-traversal guard confines
    reads to whichever root is chosen."""
    import os
    from pathlib import Path

    root = os.environ.get("QA_REPO_DIR", "")
    return FixtureRepo(Path(root) if root else REPO_DIR)


def build_graph(*, checkpointer=None, board=None, diffs=None, repo=None, retriever=None):
    board = board or default_board()
    diffs = diffs or FixtureDiffs(DIFFS_DIR)
    repo = repo or _default_repo()
    if retriever is None:
        from qa_agent.rag import build_retriever  # deferred: needs OPENAI_API_KEY

        retriever = build_retriever()

    builder = StateGraph(EpisodeState)
    builder.add_node("intake", make_intake(board))
    builder.add_node("retrieve", make_retrieve(retriever))
    builder.add_node("fetch_diff", make_fetch_diff(diffs))
    builder.add_node("review", make_review(repo))
    builder.add_node("human_gate", human_gate)
    builder.add_node("post", make_post(board))

    builder.add_edge(START, "intake")
    # path_map lists declare the possible targets so get_graph()/Mermaid can
    # render the conditional edges; routing itself is the router's return value.
    builder.add_conditional_edges(
        "intake", route_after_intake, ["retrieve", "fetch_diff", END]
    )
    builder.add_edge(["retrieve", "fetch_diff"], "review")
    builder.add_edge("review", "human_gate")
    builder.add_conditional_edges("human_gate", route_after_gate, ["post", "review", END])
    builder.add_edge("post", END)

    return builder.compile(checkpointer=checkpointer)
