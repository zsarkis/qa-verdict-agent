# QA Verdict Runbook

How we review a diff against a ticket's acceptance criteria. The verdict is a contract:
every AC gets an explicit status, every status gets cited evidence from the diff.

## Reading acceptance criteria

- Read ACs literally. "10 or more" means `>= 10`. "More than 10" means `> 10`. Boundary
  language in ACs is exact — when a diff and an AC disagree on a boundary, the diff fails.
- An AC is judged only on what can be verified. If the diff plus available code context
  cannot confirm or deny an AC, the status is **unclear**, not a guess.

## Fail vs. unclear

- **fail**: the AC is verifiably not met by the diff (wrong behavior, missing behavior,
  or a regression of behavior the ticket promised to preserve).
- **unclear**: the AC references a value, policy, or behavior that is defined nowhere in
  the ticket, the diff, or team documentation. Do not fill gaps with assumptions — flag
  them. A ticket with any unclear AC goes back to its author for information, it does not
  merge.

## Money handling (hard rule)

All currency amounts must be **rounded half-even to 2 decimal places** — never truncated.
Python's built-in `round(x, 2)` does this; truncating via `int(x * 100) / 100` or
`math.floor` is a defect **even when the accompanying tests pass**, because truncation
errors compound across line items and reconciliation. New money-heavy code should prefer
`decimal.Decimal` with `ROUND_HALF_EVEN`. A diff that computes a currency amount by
truncation fails the AC that covers that amount, regardless of test status.

## Regressions

A diff under review is responsible for what it removes, not just what it adds. Deleted
validation, deleted error handling, or deleted tests are treated as regressions unless the
ticket explicitly calls for the removal.
