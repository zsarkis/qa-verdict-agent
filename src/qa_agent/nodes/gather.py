"""The parallel gather branch: retrieve (KB) and fetch_diff (port).

These run concurrently after intake and write disjoint state keys (`context`,
`diff`), so no reducers are needed. A missing diff fixture raises — that's a
broken fixture, not a business condition (DECISIONS.md §16).
"""

from qa_agent.ports.diffs import DiffSource


def make_retrieve(retriever):
    def retrieve(state: dict) -> dict:
        ticket = state["ticket"]
        query = ticket["title"] + "\n" + "\n".join(
            ac["text"] for ac in ticket["acceptance_criteria"]
        )
        docs = retriever.invoke(query)
        return {
            "context": [
                {"text": d.page_content, "source": d.metadata.get("source", "unknown")}
                for d in docs
            ]
        }

    return retrieve


def make_fetch_diff(diffs: DiffSource):
    def fetch_diff(state: dict) -> dict:
        return {"diff": diffs.get_diff(state["ticket"]["diff_ref"])}

    return fetch_diff
