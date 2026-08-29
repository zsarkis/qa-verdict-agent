"""Graph-shape tests: wiring, not LLM behavior. Ports and retriever are fakes
so this runs keyless and offline."""

from qa_agent.graph import build_graph


class FakeRetriever:
    def invoke(self, query):
        return []


def compiled():
    return build_graph(retriever=FakeRetriever())


def test_graph_has_expected_nodes():
    nodes = set(compiled().get_graph().nodes)
    assert {"intake", "retrieve", "fetch_diff", "review", "human_gate", "post"} <= nodes


def test_gather_branch_fans_in_to_review():
    edges = compiled().get_graph().edges
    into_review = {e.source for e in edges if e.target == "review"}
    assert {"retrieve", "fetch_diff"} <= into_review


def test_gate_routes_to_post_review_and_end():
    edges = compiled().get_graph().edges
    from_gate = {e.target for e in edges if e.source == "human_gate"}
    assert {"post", "review", "__end__"} <= from_gate
