# Testing Conventions

- **Behavior changes require test changes.** Any diff that changes observable behavior must
  add or update tests covering that behavior. A behavior change with untouched tests is
  incomplete.
- **Boundaries must be tested at the boundary.** A rule that activates at a threshold
  (e.g. "free shipping at 10 items") needs a test at exactly the threshold value, not just
  comfortably above it. A passing test at 12 items proves nothing about 10.
- **Bug fixes require a regression test** that fails on the old code and passes on the new.
- **Test names state the rule**, not the mechanics: `test_shipping_free_at_threshold`, not
  `test_shipping_2`.
- Tests passing is necessary, never sufficient. Tests encode the author's understanding of
  the requirement — QA's job is to check that understanding against the AC, including the
  cases the author didn't think to test.
