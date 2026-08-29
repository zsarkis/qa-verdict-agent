"""GitHub Issues adapter for the TicketBoard port.

Mixed reality, stated openly: the BOARD is real (issues on a real repo), the
code under review stays the fixture app — the issue's `Diff-Ref:` line points
at a local fixture diff. Swapping in real PR diffs is the GitHubDiffs
improvement, not this adapter's job.

Issue contract (what makes an issue a reviewable ticket):
- a `ready-for-qa` label — its absence is a business error (routes to END),
  same taxonomy as the file board's status check
- a `## Acceptance Criteria` section with checklist lines:
      - [ ] AC-1: limit/offset pagination with defaults
  (ids optional; unlabeled criteria are auto-numbered in order)
- a `Diff-Ref: QA-103.diff` line naming the fixture diff

Auth: GITHUB_TOKEN env (a fine-grained token with issues read/write on the
target repo; `gh auth token` works). Ticket id = the issue number, so
`make run TICKET=17` and thread_id follow the same convention as file tickets.
"""

import os
import re
from typing import Protocol

import requests

API = "https://api.github.com"

AC_LINE = re.compile(r"^\s*-\s*\[[ xX]?\]\s*(?:(AC-\d+)\s*:\s*)?(.+?)\s*$")
AC_HEADING = re.compile(r"^\s*#{2,3}\s*acceptance criteria\s*$", re.IGNORECASE)
DIFF_REF = re.compile(r"^\s*diff-ref\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
READY_LABEL = "ready-for-qa"


class BoardTransport(Protocol):
    def get(self, path: str): ...  # dict for a single issue, list for a listing

    def post(self, path: str, payload: dict) -> dict: ...


class GitHubTransport:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get(self, path: str):
        response = self.session.get(f"{API}{path}", timeout=30)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict) -> dict:
        response = self.session.post(f"{API}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


def parse_issue_body(body: str) -> tuple[str, list[dict], str | None]:
    """Split an issue body into (description, acceptance_criteria, diff_ref)."""
    lines = (body or "").splitlines()
    description: list[str] = []
    criteria: list[dict] = []
    in_ac = False
    for line in lines:
        if AC_HEADING.match(line):
            in_ac = True
            continue
        if in_ac and line.lstrip().startswith("#"):
            in_ac = False  # next heading ends the AC section
        if in_ac:
            match = AC_LINE.match(line)
            if match:
                ac_id = match.group(1) or f"AC-{len(criteria) + 1}"
                criteria.append({"id": ac_id, "text": match.group(2)})
            continue
        if DIFF_REF.match(line):
            continue  # captured separately below; keep out of the description
        description.append(line)
    ref_match = DIFF_REF.search(body or "")
    diff_ref = ref_match.group(1) if ref_match else None
    return "\n".join(description).strip(), criteria, diff_ref


def render_verdict_comment(verdict: dict) -> str:
    status_icon = {"pass": "✅", "fail": "❌", "needs_info": "❓"}
    lines = [f"## QA Verdict: {status_icon.get(verdict['overall'], '')} `{verdict['overall']}`", ""]
    for result in verdict["ac_results"]:
        icon = {"pass": "✅", "fail": "❌", "unclear": "❓"}[result["status"]]
        lines.append(f"**{result['ac_id']}: {icon} {result['status']}** — {result['reasoning']}")
        for ev in result["evidence"]:
            lines.append(f"  - evidence: `{ev}`")
        lines.append("")
    lines.append(f"**Summary:** {verdict['summary']}")
    footer = [f"review attempt {verdict['attempts']}"]
    if verdict.get("consulted"):
        footer.append(f"files consulted beyond the diff: {', '.join(verdict['consulted'])}")
    if verdict.get("redaction_log"):
        footer.append(f"redacted from ticket text: {', '.join(verdict['redaction_log'])}")
    lines.append("")
    lines.append("_" + " · ".join(footer) + "_")
    lines.append("_posted by qa-verdict-agent after human approval_")
    return "\n".join(lines)


class GitHubBoard:
    """TicketBoard adapter over GitHub Issues. Ticket id = issue number."""

    def __init__(self, repo: str, transport: BoardTransport | None = None):
        self.repo = repo
        if transport is None:
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise RuntimeError(
                    "GITHUB_TOKEN is required for QA_BOARD=github (try: gh auth token)"
                )
            transport = GitHubTransport(token)
        self.transport = transport

    def get_ticket(self, ticket_id: str) -> dict:
        number = ticket_id.lstrip("#")
        if not number.isdigit():
            raise KeyError(f"GitHub tickets are issue numbers, got {ticket_id!r}")
        issue = self.transport.get(f"/repos/{self.repo}/issues/{number}")
        labels = {label["name"] for label in issue.get("labels", [])}
        description, criteria, diff_ref = parse_issue_body(issue.get("body", ""))
        return {
            "id": str(issue["number"]),
            "title": issue.get("title", ""),
            "type": "issue",
            # status mirrors the file board's contract: intake checks it and
            # routes a business error to END when the label is missing
            "status": "ready_for_qa" if READY_LABEL in labels else f"missing '{READY_LABEL}' label",
            "body": description,
            "acceptance_criteria": criteria,
            "diff_ref": diff_ref,
        }

    def post_verdict(self, ticket_id: str, verdict: dict) -> dict:
        number = str(ticket_id).lstrip("#")
        comment = self.transport.post(
            f"/repos/{self.repo}/issues/{number}/comments",
            {"body": render_verdict_comment(verdict)},
        )
        return {"posted": True, "location": comment.get("html_url", "")}

    def list_ready(self) -> list[str]:
        issues = self.transport.get(
            f"/repos/{self.repo}/issues?labels={READY_LABEL}&state=open&per_page=50"
        )
        # the issues endpoint returns PRs too; a PR is not a ticket
        return [str(i["number"]) for i in issues if "pull_request" not in i]
