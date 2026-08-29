"""CLI entry point.

    run <ticket-id>      open an episode (or continue an in-flight one — the
                         kill/resume demo is literally running this twice)
    resume <ticket-id>   answer the human gate:
                         --decision approve|revise|abort [--notes "..."]

Streaming: stream_mode=["updates", "messages"] — node-by-node progress plus
live tool-call visibility from the review agent (--tokens adds raw model
tokens). Interrupts are detected via the "__interrupt__" key in updates
(classic stable API; stream_events v3 is experimental — deliberate
non-adoption).

Thread semantics: thread_id = ticket_id. A killed or gated episode continues
with `run`; a completed episode says so and stays done (one live episode per
ticket — documented limitation, prod would use episode UUIDs).
"""

import argparse
import os
import sys
import time

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from qa_agent.graph import build_graph, default_board
from qa_agent.settings import CHECKPOINT_DB


def _config(ticket_id: str) -> dict:
    return {
        "configurable": {"thread_id": ticket_id},
        "metadata": {
            "ticket_id": ticket_id,
            "review_mode": os.environ.get("QA_REVIEW_MODE", "tool"),
            "app": "qa-verdict-agent",
        },
        "tags": ["qa-verdict"],
    }


def _print_update(node: str, update: dict) -> None:
    if node == "intake":
        if update.get("error"):
            print(f"● intake      error: {update['error']}")
        else:
            ticket = update["ticket"]
            redactions = ", ".join(update["redaction_log"]) or "none"
            print(f"● intake      {ticket['id']}: {ticket['title']}  (redacted: {redactions})")
    elif node == "retrieve":
        sources = sorted({c["source"] for c in update["context"]})
        print(f"● retrieve    {len(update['context'])} chunks from {', '.join(sources)}")
    elif node == "fetch_diff":
        print(f"● fetch_diff  {len(update['diff'].splitlines())} lines of diff")
    elif node == "review":
        statuses = ", ".join(
            f"{r['ac_id']}={r['status']}" for r in update["verdict"]["ac_results"]
        )
        for path in update.get("consulted", []):
            print(f"  ↳ review read {path} via get_file_context")
        print(f"● review      overall={update['overall']}  ({statuses})  attempt {update['attempts']}")
    elif node == "human_gate":
        print(f"● human_gate  decision={update['decision']}")
    elif node == "post":
        print(f"● post        verdict written to {update['post_result']['location']}")
    else:
        print(f"● {node}")


def _print_interrupt(payload: dict) -> None:
    print("\n─── awaiting human decision " + "─" * 34)
    print(f"ticket:  {payload['ticket_id']}   draft overall: {payload['overall']}"
          f"   (review attempt {payload['attempts']})")
    for result in payload["verdict"]["ac_results"]:
        print(f"  {result['ac_id']}: {result['status']:8s} {result['reasoning']}")
        for ev in result["evidence"]:
            print(f"      evidence: {ev}")
    print(f"summary: {payload['verdict']['summary']}")
    if payload.get("consulted"):
        print(f"files consulted beyond the diff: {', '.join(payload['consulted'])}")
    print("─" * 62)
    print(
        f"resume with:  make resume TICKET={payload['ticket_id']} "
        'DECISION=approve|revise|abort [NOTES="..."]'
    )


def _stream(graph, payload, config, show_tokens: bool) -> None:
    for mode, chunk in graph.stream(payload, config, stream_mode=["updates", "messages"]):
        if mode == "updates":
            for node, update in chunk.items():
                if node == "__interrupt__":
                    _print_interrupt(update[0].value)
                else:
                    _print_update(node, update or {})
        else:
            message, _meta = chunk
            # Tool calls arrive as full AIMessages (.tool_calls) when the inner
            # agent invokes non-streaming, or as chunks (.tool_call_chunks)
            # when tokens stream — handle both.
            for tc in getattr(message, "tool_calls", []) or []:
                args = ", ".join(f"{k}={v!r}" for k, v in (tc.get("args") or {}).items())
                print(f"  ↳ review is calling {tc['name']}({args})")
            for tc in getattr(message, "tool_call_chunks", []) or []:
                if tc.get("name"):
                    print(f"  ↳ review is calling {tc['name']}(...)")
            if show_tokens and isinstance(getattr(message, "content", None), str):
                sys.stdout.write(message.content)
                sys.stdout.flush()


def cmd_run(args) -> None:
    with SqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        config = _config(args.ticket_id)
        snapshot = graph.get_state(config)
        if snapshot.values and not snapshot.next:
            outcome = snapshot.values.get("post_result") or snapshot.values.get("error") \
                or f"decision={snapshot.values.get('decision')}"
            print(f"episode for {args.ticket_id} already complete: {outcome}")
            print(f"(one live episode per ticket; delete {CHECKPOINT_DB.name} to rerun)")
            return
        if snapshot.next:
            print(f"continuing in-flight episode for {args.ticket_id} "
                  f"(resuming at: {', '.join(snapshot.next)})")
            payload = None  # continue from the checkpoint
        else:
            payload = {"ticket_id": args.ticket_id}
        _stream(graph, payload, config, args.tokens)


def cmd_resume(args) -> None:
    with SqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        config = _config(args.ticket_id)
        snapshot = graph.get_state(config)
        if not snapshot.next:
            print(f"nothing to resume for {args.ticket_id} — no episode waiting at the gate")
            return
        resume_value = {"decision": args.decision}
        if args.notes:
            resume_value["notes"] = args.notes
        _stream(graph, Command(resume=resume_value), config, args.tokens)


def cmd_watch(args) -> None:
    """Poll the board; open an episode for every ready-for-qa ticket that
    doesn't have one. The polling loop is the local stand-in for a PR-opened /
    card-moved webhook — the graph is trigger-agnostic, so a webhook receiver
    would call the exact same code path."""
    board = default_board()
    with SqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        graph = build_graph(checkpointer=checkpointer, board=board)
        backend = os.environ.get("QA_BOARD", "file")
        print(
            f"watching the {backend} board every {args.interval}s — "
            "mark a card ready-for-qa and it gets picked up (ctrl-c to stop)"
        )
        announced: set[str] = set()
        try:
            while True:
                try:
                    ready = board.list_ready()
                # OSError covers requests' network/HTTP errors (RequestException
                # subclasses IOError); ValueError covers corrupt fixture JSON.
                # A poll blip shouldn't kill a long-running watcher.
                except (OSError, ValueError) as exc:
                    print(f"! board poll failed ({exc}); retrying in {args.interval}s")
                    time.sleep(args.interval)
                    continue
                for ticket_id in ready:
                    config = _config(ticket_id)
                    snapshot = graph.get_state(config)
                    if snapshot.values and not snapshot.next:
                        continue  # episode already finished
                    if snapshot.next:
                        if ticket_id not in announced:
                            print(
                                f"· {ticket_id} waiting at {', '.join(snapshot.next)} — "
                                f"make resume TICKET={ticket_id} DECISION=..."
                            )
                            announced.add(ticket_id)
                        continue
                    print(f"\n▶ picked up ready-for-qa ticket {ticket_id}")
                    _stream(graph, {"ticket_id": ticket_id}, config, args.tokens)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nwatch stopped")


def main() -> None:
    parser = argparse.ArgumentParser(prog="qa-agent", description="QA verdict agent")
    parser.add_argument("--tokens", action="store_true", help="stream raw model tokens")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="open (or continue) a QA episode")
    run.add_argument("ticket_id")
    run.set_defaults(fn=cmd_run)

    resume = sub.add_parser("resume", help="answer the human gate")
    resume.add_argument("ticket_id")
    resume.add_argument("--decision", choices=["approve", "revise", "abort"], required=True)
    resume.add_argument("--notes", default="")
    resume.set_defaults(fn=cmd_resume)

    watch = sub.add_parser("watch", help="poll the board and open episodes as cards become ready")
    watch.add_argument("--interval", type=int, default=15, help="poll interval in seconds")
    watch.set_defaults(fn=cmd_watch)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
