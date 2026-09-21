# Design: progress-tests (Python library)

Design session date: 2026-09-20. Terminology used throughout this doc is
defined in `../LANGUAGE.md`.

Input to this session: `../../../claude-config/practices/progressive-test/
progressive-test-standard.md`, `.../progressive-table-test/
progressive-table-test-standard.md`, and `.../progressive-test/
python-library-notes.md` (a handoff document from a real Python port,
not a design). This doc is the resolution of that handoff, item by item,
plus everything decided beyond it.

## Language & tooling

- Python. No other language was seriously in the running once evaluated
  against this library's actual use case (hand-written migration/rollout
  checks) — Go's static-binary distribution story matters most when the
  *test consumer* is a Go binary, not when a human is authoring one-off
  checks, so it didn't win out despite good concurrency primitives.
- Built and packaged with `uv`; linted/formatted with `ruff`.
- Package name `progress-tests` (PyPI), imported as `progress_tests`.
- The runner is a bundled console script, `progress-tests`. See
  "Runner: from pytest to a custom console script" below for why this
  supersedes the original all-`pytest` decision.

## Core model

- A **step** is a function decorated `@step("NAME")`, taking exactly one
  positional argument (the current input) and returning a `Status`
  (`PASS`/`WAIT`/`FAIL` — a real enum internally, never a bare string).
- Steps form a **strict linear list** — no dependency graph, no
  `depends_on` field. A step's position in the list only orders the
  table's columns and the sequence data flows through; it is no longer
  a gate. Revised 2026-09-22 (see "Every step always runs" below):
  every step is evaluated for every input regardless of any other
  step's result, so a step reading data an earlier step would have
  contributed is gated by that data actually being present (which
  fails structurally — see below), not by the runner stopping early on
  its behalf.
- No first-class support for conditional/escalation steps that sit
  outside the main gating chain (e.g. a stop-gap escalation that only
  fires if an earlier step stalls). Write those as ordinary code outside
  the library if needed.
- `Status` stays exactly 3-valued **as a kind** — `PASS`/`WAIT`/`FAIL`.
  No confidence/sampling annotation for checks that only sample live
  state (e.g. a high-volume log stream) — the check author's own
  return value is the final word on what "pass" means for their check.
  Each kind carries an optional message and an optional detail; see
  "Status messages" below.
- A step returns `Status`, optionally paired with a `dict` of data for
  later steps on the same input: `return Status.PASS("bucket ready"),
  {"example_key": "example_value"}`. That data is merged into the input
  passed to subsequent steps. If a step's returned data would overwrite an
  existing key — from the original input, or from an earlier step —
  `invoke()` raises `ValueError` immediately rather than silently
  picking one value: any ambiguity about which value wins is treated as
  an authoring bug, not something to resolve quietly. Implemented
  2026-09-20 (was deferred out of the initial v1 pass).

## `@step` decorator

Validates and wraps a single function, at decoration time:

- Enforces exactly one positional argument.
- Wraps the call so that **any exception, or any return value that
  isn't a `Status` member, becomes `Status.FAIL` automatically.** This
  is the mechanism that makes "unimplemented is `fail`, never `wait`"
  true by construction — there is no code path that produces `wait`
  except an explicit `return Status.WAIT`.
- The auto-generated `Status.FAIL` carries a short message identifying
  the known cause — `"assert fail"` for `AssertionError`, `"exception"`
  for any other exception type, `"invalid step return value"` for a
  return that isn't `Status` or `(Status, dict)` — plus the full
  traceback (for the two exception cases) as `detail`, which `invoke()`
  prints after the table rather than immediately to stderr. See "Status
  messages" below.

## Status messages

Added 2026-09-21, message made required later the same day, then
changed to default to `""` shortly after that (three passes in one
day): the first cut let `message` default to `None` and fall back to
the word `pass`/`wait`/`fail` — dropped once real usage showed every
step should say what it actually found, not just its kind. Making it
required (no default at all, `TypeError` if omitted) was the next
attempt, but that forced a message even on a step with nothing more
useful to say than its glyph. `message: str = ""` is the settled
answer: still no silent fallback to a generic word, but a step can
opt out of a message entirely rather than being forced to invent one.

A `Status` is a kind (`PASS`/`WAIT`/`FAIL`, a private `_Kind` enum)
plus a `message: str = ""` and an optional `detail: str | None`.
`Status.PASS`, `Status.WAIT`, `Status.FAIL` are classmethods, not
values — each *builds* a `Status` of that kind: `Status.WAIT("waiting
on backup")`, or `Status.PASS()` for no message. Forgetting to call
one at all (`return Status.PASS`, leaving the bound method itself)
still fails structurally — `_normalize` only accepts an actual
`Status` instance, so an uncalled classmethod reference falls into the
same "invalid step return value" path as any other malformed return.

Two `Status`es are equal (ordinary dataclass equality) only when kind
*and* message match — `Status.FAIL("boom") != Status.FAIL("other")`.
Internal comparisons that only care about kind (`invoke()`'s
`fail_on_wait` check, `render.py`'s glyph/color lookup) compare
`status.kind` against `_Kind` directly rather than relying on `Status`
equality.

- **Where it renders**: a non-empty `message` replaces the table
  cell's word — `+ <message>`, `! <message>`, `X <message>`, in the
  status's usual color. An empty `message` renders as the bare glyph
  (`+`/`!`/`X`) with nothing after it — not the word `pass`/`wait`/
  `fail`, which was the earlier, rejected default. This was also a
  deliberate choice against a separate "details" section under the
  table for short messages: they're meant to be scannable at a glance,
  in place, not looked up elsewhere.
- **Column width**: not a fixed function of the status word — 
  `render_table` measures the actual rendered width of every cell in a
  column (including its message) and widens the column to fit the
  longest one. This also fixed a real bug (`render.py`'s old
  `status_word_width` calculation didn't account for the glyph+space
  prefix, so any step name shorter than `"+ wait"` produced a column
  narrower than what actually printed, drifting every column after
  it — found via real output once step names got shortened).
- **Keep messages short** — aim for well under 12 characters. They
  render inline in a fixed-width column, and a long one widens that
  column for every row, not just the one that needed it. Not enforced
  (no truncation) — a documented expectation on step authors,
  consistent with this library's general stance of trusting the caller
  rather than validating what it can't usefully validate. The goal
  isn't the shortest possible string, it's short *and* meaningful —
  `"ok"`/`"waiting"` over nothing, but not padded out with words the
  reader doesn't need either.
- **`detail`**: a longer, optional payload (typically a traceback) not
  shown in the table at all — `invoke()` prints it once, after the
  whole table, labeled by input and step name. Keeps the table itself
  a stable, scannable grid regardless of how much detail a failure
  carries, and keeps a stack trace from interleaving with table output
  the way pytest's own capture used to (see "Runner" section above).
  Available to any step, not just the framework's own exception
  handling — `Status.FAIL("bucket missing", detail="...")` is a
  supported call.

## `invoke()` — the engine

```python
from progress_tests import step, Status, invoke


@step("BUCKET_EXISTS")
def bucket_exists(case) -> Status:
    if s3_bucket_exists(case["bucket"]):
        return Status.PASS("bucket ready")
    return Status.WAIT("bucket not created yet")


@step("DNS_CUTOVER")
def dns_cutover(case) -> Status:
    if dns_points_at_new_host(case["bucket"]):
        return Status.PASS("DNS cut over")
    return Status.WAIT("DNS not cut over yet")


def test_migration():
    steps = [bucket_exists, dns_cutover]
    inputs = [
        {"name": "instance-a", "bucket": "a-bucket"},
        {"name": "instance-b", "bucket": "b-bucket"},
    ]
    invoke(steps, inputs, fail_on_wait=True)
```

- `invoke(steps, inputs, fail_on_wait=False)` is called once inside an
  ordinary, no-argument `test_*` function. `steps` and `inputs` are
  local to that test function, not module-level globals — step
  functions themselves stay at module scope so they can be reused
  across multiple tests in a file.
- No per-input subtest identity. Each input does **not** become its own
  independently-reported test; `invoke()` owns the whole input list and
  the whole `test_*` function is one unit of pass/fail as far as the
  runner is concerned. This was a deliberate trade against Go-style
  subtests: getting per-input test identity while still rendering one
  unified table would require real reporter-level machinery, which lost
  out to "just render the table" simplicity.
- Validates the composed list at call time (this can only happen once
  the whole list is visible, unlike the decorator's per-function
  checks): rejects duplicate `STEP_NAME`s, and rejects duplicate input
  names, since both would produce ambiguous table identifiers.
- For each input independently: walks `steps` in order, evaluating
  every one regardless of any other step's result — see "Every step
  always runs" below.
- Input row label is `input["name"]`, falling back to `input[{i}]`
  (by position) when `"name"` is absent.
- Renders one color-coded table to stdout: one row per input, one
  column per `STEP_NAME` in first-seen order, and ANSI coloring,
  column-aligned. Glyphs are plain ASCII (`+`/`!`/`X`) rather than the
  shared standard's `✓`/`!`/`✗` — those aren't reliably single-width
  across terminals/fonts despite looking that way in isolation (found
  by a real misaligned table, not a theoretical concern), so this
  library diverges from the standard's suggested glyphs on purpose.
- Color is **on by default, unconditionally** — not gated by
  `sys.stdout.isatty()` or a `CI` env var check. Revised 2026-09-22:
  the original tty-detection default broke a real workflow (`watch
  --color progress-tests example` showed no color, since `watch`
  captures the child's stdout through a pipe, so `isatty()` is always
  false there regardless of the terminal `watch` itself is drawn in —
  there is no way for a `--color`-style flag on `watch`'s side to
  produce color the wrapped command never emitted). Off via `NO_COLOR`
  (the environment variable) or `--no-color` (the CLI flag, added the
  same day now that the library owns a real CLI — see "No CLI flags"
  below). The `CI` env var check was dropped as redundant with the
  general-purpose `--no-color`/`NO_COLOR` mechanism.
- Pass/fail policy, per input, based on the set of kinds among *all*
  of that input's step results (not just one "stopping" status — see
  "Every step always runs" below):
  - every step `pass` — fine.
  - any step `wait`, none `fail` — does not fail the test, by default.
    This is the expected, common state for an in-progress migration.
  - any step `fail` — always fails the test, unconditionally.
  - `fail_on_wait=True` promotes any `wait` to a failure too, for the
    one test that opts into it.
- `invoke()` raises when the test should fail; it has no exit-code logic
  of its own. The runner's own exit code (0 if everything passed, 1 if
  anything failed or raised) is the entire CI-integration story.
- No stderr `STEP_NAME:class` line output. This is an intentional
  divergence from `progressive-test-standard.md`'s shell-oriented
  contract — dropped, not carried forward, since this library owns a
  private practices standard rather than a community one.

## Every step always runs

Revised 2026-09-22, reversing the original "stop at the first
non-pass" behavior (see "Rejected: DAG/dependency generalization"
below, which this supersedes). `_evaluate()` now runs every step in
`steps`, in order, for every input, regardless of any earlier step's
result. A step's position still orders the table's columns and the
sequence data flows through (`_merge()` still only merges a step's
returned data on `PASS`), but it no longer gates whether a later step
is even attempted.

Rationale: the whole design point of a progressive test is that it's
testable from the start — every step should be exercisable and show a
real result for every input, not hide behind blank cells because an
unrelated earlier step hasn't passed yet. The old behavior also hid
genuinely useful information: a step three positions after a stalled
one might already be true (e.g. someone manually finished a later
stage out of order), and the old table simply never said so.

The real cost: a step that reads case data an earlier step would have
contributed (via its `PASS` return's data dict) can no longer assume
that data exists, since the earlier step may not have reached `PASS`.
Reading a missing key raises `KeyError`, which `@step`'s existing
exception handling already turns into `Status.FAIL("exception", ...)`
with a traceback printed after the table — no new mechanism needed,
but a step author who doesn't defend against this gets a `FAIL` for
what's really just "still in progress," which is misleading. `@step`
does not auto-detect or handle this on the author's behalf.

A small `wait_for_case_data(case, *keys)` helper (returning
`Status.WAIT` when any key is missing, `None` otherwise, for use as an
early-return guard) was proposed and built the same day, then
**rejected** — no shortcut method for this. A step that depends on
prior data guards itself with ordinary code instead, e.g.
`example/test_pipeline.py`'s `UPGRADED` step checks `"version" not in
case` before reading `case["version"]`. There is no library-provided
helper for this — it's on the step author to notice and guard against,
the same as any other data-dependency bug.

## Explicitly out of scope for v1

- No built-in checks or log-format parsers (S3 access logs, CloudFront,
  ALB). Pure framework — bring your own (e.g. `boto3`) inside your own
  step functions.
- No CLI flags beyond an optional discovery path and `--no-color`
  (added 2026-09-22, see the color bullet above — a real, narrow need
  once the library owned its own CLI, not a general flags system). No
  fixtures, no parametrize, no plugin system of any kind.
- No dependency graph/DAG.
- No cross-language stderr contract.

## Runner: from pytest to a custom console script

Revised 2026-09-20, superseding the original "the runner is plain
pytest" decision above.

While building `example/test_pipeline.py`, we hit a real, structural
problem: pytest's terminal reporter writes a progress marker (a `.` per
test, or the full nodeid in `-v`) with no trailing newline, and it lands
on the same line as whatever a test prints in real time via `-s`.
Confirmed empirically across `-s`, `-s -q`, and `-s -v`: **every**
table's header line got a pytest marker glued onto its front the moment
there was more than one progressive test in a session. There's no
code-level workaround from inside a step or test function — even
writing directly to `sys.__stdout__` gets caught by pytest's default
fd-level capture. Patching around this further (custom pytest plugin
hooking the terminal reporter, disabling capture globally, etc.) was
rejected as more machinery than the problem deserves; the simpler fix
is to not hand stdout to a tool that doesn't fully cooperate with it.

Decision: the library ships its own runner as a console script,
`progress-tests [path] [--no-color]` (`src/progress_tests/cli.py`,
wired up via `[project.scripts]`):

- **Discovery**: walk `path` (default: cwd) for `test_*.py`/`*_test.py`
  files, import each one, and collect its top-level `test_*` functions
  (checked by `__module__` so a function merely imported into a file
  isn't double-collected). Call each with zero arguments.
- **No fixtures, no parametrize, no plugin system.** `invoke()` already
  raises `AssertionError` on real failure, so "did it raise" is the
  whole pass/fail signal; any other exception is also caught and
  counted as a failure (with its traceback printed), rather than
  crashing the whole run.
- **Output**: since the runner fully owns stdout, there's no
  interleaving problem — print each test's label, then let it run (its
  own `invoke()` call prints the table), then a blank line, repeating
  for every discovered test, then a final `N passed[, M failed]`
  summary line. Exit 0 if nothing failed, 1 otherwise.
- **One table per test function**, not one aggregated table across all
  discovered tests — different tests likely have different step/column
  shapes (different steps, different case data), so a combined table
  would need to reconcile heterogeneous columns or force a
  lowest-common-denominator layout. Simpler to keep them separate,
  matching everything built so far.

This only changes how a library *consumer's* progressive tests are run.
The library's own dev/test suite (`tests/`) keeps using pytest
(`uv run pytest`) — that's how `invoke()`/`step()` themselves are
verified, a separate concern from what tool consumers use to run their
progressive tests.

## Rejected: DAG/dependency generalization

`python-library-notes.md` item #0 proposed generalizing "stop at first
non-pass" into a real dependency graph: a `depends_on` field per step,
short-circuiting to `wait` based on declared edges instead of list
position, *and* evaluating every step every run. Split in two at the
time and both halves rejected together; only one half stayed rejected.

- The `depends_on`/graph half is still rejected: steps stay a **plain
  ordered list**, no DAG, no per-step dependency declarations. That
  keeps table-column order stable (declaration order) and test
  authoring simple — correctly modeling forks/joins was never worth
  the added authoring/data-flow complexity for this library's actual
  use case (hand-written migration checks, not a build system).
- The "evaluate every step every run" half was re-litigated and
  **adopted** 2026-09-22 — see "Every step always runs" above. The
  original reasoning for rejecting it ("a step that doesn't really
  depend on its immediate predecessor still gets gated behind it,
  accepted as a guardrail toward simpler workflows") didn't survive
  contact with a real progressive test: hiding a later step's true,
  already-reachable state behind an earlier stalled one actively hid
  information a fully-testable-from-the-start design is supposed to
  surface. Losing the old "short-circuit protects you from missing
  data" guarantee is accepted as the cost — see "Every step always
  runs" above for what replaces it (ordinary step-author-written
  guards, no library helper).

## Resolution of `python-library-notes.md`, item by item

- **0 (DAG/fork-join generalization):** Split. The `depends_on`/graph
  half stays rejected; the "evaluate every step every run" half was
  adopted 2026-09-22 — see "Rejected: DAG/dependency generalization"
  above.
- **1 (two faces: function + CLI):** Adopted, in a different shape than
  proposed. A step is a plain decorated function called via `invoke()`
  inside an ordinary `test_*` function; the "CLI face" is the bundled
  `progress-tests` runner (discovery + invocation), not per-step CLI
  flags. See "Runner: from pytest to a custom console script" above.
- **2 (real enum internally):** Adopted. `Status.PASS`/`WAIT`/`FAIL`.
- **3 (parallelize rows by default):** Dropped. `invoke()` runs inputs
  sequentially; there's no CLI/watch mode to make this matter yet.
- **4 (--watch stdout flush):** N/A. No `--watch` mode; `invoke()` is a
  synchronous library call, not a long-running CLI process.
- **5 (structured config format):** N/A. Inputs are plain Python data
  declared inside the test function, not an external config file.
- **6 (None vs [] distinction):** Adopted, for free — Python's own
  `None`/`{}`/`[]` carry this distinction natively; no sentinel needed.
- **7 (unimplemented is fail, never wait):** Adopted, enforced
  structurally by the `@step` decorator's exception/bad-return wrapping.
- **8 (reusable log-format parsers):** Rejected for v1. Pure framework.
- **9 (confidence/sampling state):** Rejected. `Status` stays exactly
  3-valued.
- **10 (conditional/escalation steps):** No first-class support.
- **11 (render_table primitive):** Adopted — `invoke()` renders the
  color-coded table directly as part of its own behavior.

## Open follow-ups (tracked in `TODO.md`)

- Whether duplicate-input-name rejection is too strict in practice —
  revisit once there's real usage.
