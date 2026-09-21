# TODO

See `docs/design/progressive-tests-library.md` for the full design.

## Needs your feedback

- The README (and once, TODO.md) looked empty/stale to you, even though
  disk, the git commit, and `origin/main` all show the full content
  byte-for-byte (verified via hash/hexdump each time). Ruled out: a
  directory mismatch — confirmed your shell's `pwd` matches this repo.
  Still unconfirmed: whether it's a stale editor tab from when README
  was first created as a bare stub. Run `! cat README.md` here to check
  we're looking at the same bytes.

## Backlog

- Revisit whether `invoke()` rejecting duplicate input names is too
  strict once there's real usage — currently rejected for the same
  reason as duplicate `STEP_NAME`s (ambiguous table labels).

