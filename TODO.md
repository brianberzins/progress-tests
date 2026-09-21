# TODO

See `docs/design/progressive-tests-library.md` for the full design.

## Needs your feedback

- The README looked empty/stale to you twice, even though disk, the
  git commit, and `origin/main` all show the full content byte-for-byte
  (verified via hash/hexdump). Best guess is a stale editor tab from
  when it was first created as a bare stub. Still unconfirmed — run
  `! cat README.md` here to check we're looking at the same bytes.

## Backlog

- Let a step optionally return `(Status, dict)`, with the dict merged
  into the input passed to the next step. Deferred from v1 to keep the
  first implementation's step signature to a single `Status` return.
- Revisit whether `invoke()` rejecting duplicate input names is too
  strict once there's real usage — currently rejected for the same
  reason as duplicate `STEP_NAME`s (ambiguous table labels).

