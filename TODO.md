# TODO

See `docs/design/progressive-tests-library.md` for the full design.

- Let a step optionally return `(Status, dict)`, with the dict merged
  into the input passed to the next step. Deferred from v1 to keep the
  first implementation's step signature to a single `Status` return.
- Revisit whether `invoke()` rejecting duplicate input names is too
  strict once there's real usage — currently rejected for the same
  reason as duplicate `STEP_NAME`s (ambiguous table labels).
- Implement the library itself via TDD (see
  `../claude-config/practices/tdd/tdd-standard.md`): one red/green/
  refactor loop per behavior (decorator validation, `invoke()`
  validation, per-input evaluation, table rendering, color
  auto-detection, wait/fail policy).

