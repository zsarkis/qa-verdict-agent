"""Post the approved verdict back to the board via the port."""

from qa_agent.ports.board import TicketBoard


def make_post(board: TicketBoard):
    def post(state: dict) -> dict:
        document = {
            "ticket_id": state["ticket_id"],
            "overall": state["overall"],
            "summary": state["verdict"]["summary"],
            "ac_results": state["verdict"]["ac_results"],
            "attempts": state["attempts"],
            "consulted": state.get("consulted", []),
            "redaction_log": state["redaction_log"],
        }
        return {"post_result": board.post_verdict(state["ticket_id"], document)}

    return post
