# Definition of Done (QA verdicts)

A ticket in **Ready for QA** receives exactly one of three overall verdicts:

- **pass** — every AC has status pass, and no runbook hard rule is violated.
- **fail** — at least one AC has status fail. The verdict comment names the failing AC(s)
  and cites the diff evidence.
- **needs_info** — no AC failed, but at least one AC is unclear (unverifiable from the
  ticket, diff, and team docs). The verdict comment states exactly what information is
  missing and from whom.

Precedence: any fail makes the overall verdict fail, even if other ACs are unclear.

## Verdict comment format

Posted verdicts contain: per-AC status with one-sentence reasoning each, cited evidence
(file + hunk) for every pass/fail, and a two-to-three-sentence summary a non-engineer PM
can act on.
