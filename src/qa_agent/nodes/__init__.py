"""Graph nodes.

Nodes are closures over ports (make_* factories): the graph builder is the
composition root, nodes never construct their own dependencies, and tests
inject fakes. Each node is a function of state returning a partial update.
"""

from qa_agent.nodes.gate import human_gate
from qa_agent.nodes.gather import make_fetch_diff, make_retrieve
from qa_agent.nodes.intake import make_intake
from qa_agent.nodes.post import make_post
from qa_agent.nodes.review import make_review

__all__ = [
    "human_gate",
    "make_fetch_diff",
    "make_intake",
    "make_post",
    "make_retrieve",
    "make_review",
]
