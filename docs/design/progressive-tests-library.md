# Design: progressive-tests (Python library)

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
- Package name `progressive-tests` (PyPI), imported as `progressive_tests`.
- The runner is plain `pytest`. There is no custom CLI, no pytest
  plugin, no registered CLI flags. The library is a plain set of
  importable functions — nothing more.

## Core model

- A **step** is a function decorated `@step("NAME")`, taking exactly one
  positional argument (the current input) and returning a `Status`
  (`PASS`/`WAIT`/`FAIL` — a real enum internally, never a bare string).
- Steps form a **strict linear sequence** — no dependency graph, no
  `depends_on` field. A step's position in the list a test assembles
  *is* its dependency (it implicitly depends on the step before it).
  This is a deliberate simplicity choice, not an oversight: it nudges
  authors toward linear workflows. A workflow with a genuine fork/join
  is expected to be flattened by the test author, accepting that an
  independent branch can appear to wait behind an unrelated stalled step
  — see "Rejected: DAG/dependency generalization" below.
- No first-class support for conditional/escalation steps that sit
  outside the main gating chain (e.g. a stop-gap escalation that only
  fires if an earlier step stalls). Write those as ordinary code outside
  the library if needed.
- `Status` stays exactly 3-valued. No confidence/sampling annotation for
  checks that only sample live state (e.g. a high-volume log stream) —
  the check author's own return value is the final word on what "pass"
  means for their check.
- A step returns `Status`, optionally paired with a `dict` of data for
  later steps on the same input: `return Status.PASS, {"example_key":
  "example_value"}`. That data is merged into the input passed to
  subsequent steps. If a step's returned data would overwrite an
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

## `invoke()` — the engine

```python
from progressive_tests import step, Status, invoke


@step("BUCKET_EXISTS")
def bucket_exists(case) -> Status:
    return Status.PASS if s3_bucket_exists(case["bucket"]) else Status.WAIT


@step("DNS_CUTOVER")
def dns_cutover(case) -> Status:
    return Status.PASS if dns_points_at_new_host(case["bucket"]) else Status.WAIT


def test_migration():
    steps = [bucket_exists, dns_cutover]
    inputs = [
        {"name": "instance-a", "bucket": "a-bucket"},
        {"name": "instance-b", "bucket": "b-bucket"},
    ]
    invoke(steps, inputs, fail_on_wait=True)
```

- `invoke(steps, inputs, fail_on_wait=False)` is called once inside an
  ordinary, no-argument pytest test function. `steps` and `inputs` are
  local to that test function, not module-level globals — step
  functions themselves stay at module scope so they can be reused
  across multiple tests in a file.
- No `pytest.mark.parametrize`. Each input does **not** become its own
  independently-reported pytest test; `invoke()` owns the whole input
  list and the whole test function is one pytest test. This was a
  deliberate trade against Go-style subtests: getting per-input pytest
  identity while still rendering one unified table would require a
  `pytest_terminal_summary` hook (real plugin machinery), which lost out
  to "just a library" simplicity.
- Validates the composed list at call time (this can only happen once
  the whole list is visible, unlike the decorator's per-function
  checks): rejects duplicate `STEP_NAME`s, and rejects duplicate input
  names, since both would produce ambiguous table identifiers.
- For each input independently: walks `steps` in order, stopping at
  that input's frontier step. Steps after the frontier are not
  evaluated for that input and render as blank cells.
- Input row label is `input["name"]`, falling back to `input[{i}]`
  (by position) when `"name"` is absent.
- Renders one color-coded table to stdout: one row per input, one
  column per `STEP_NAME` in first-seen order, using the existing
  standard's glyphs (`✓`/`!`/`✗`, single-width) and ANSI coloring,
  column-aligned.
- Color auto-detects and is **not configurable**: off if
  `sys.stdout.isatty()` is false, or `NO_COLOR`/`CI` env vars are set;
  on otherwise.
- Pass/fail policy, per input's frontier step:
  - `pass` — fine.
  - `wait` — does not fail the test, by default. This is the expected,
    common state for an in-progress migration.
  - `fail` — always fails the test, unconditionally.
  - `fail_on_wait=True` promotes `wait` to a failure too, for the one
    test that opts into it.
- `invoke()` raises when the test should fail; it has no exit-code logic
  of its own. Pytest's own exit code (0 if everything passed, 1 if
  anything failed) is the entire CI-integration story.
- No stderr `STEP_NAME:class` line output. This is an intentional
  divergence from `progressive-test-standard.md`'s shell-oriented
  contract — dropped, not carried forward, since this library owns a
  private practices standard rather than a community one.

## Explicitly out of scope for v1

- No built-in checks or log-format parsers (S3 access logs, CloudFront,
  ALB). Pure framework — bring your own (e.g. `boto3`) inside your own
  step functions.
- No CLI flags, no pytest plugin, no `pytest_addoption`.
- No dependency graph/DAG.
- No cross-language stderr contract.

## Rejected: DAG/dependency generalization

`python-library-notes.md` item #0 proposed generalizing "stop at first
non-pass" into a real dependency graph (`depends_on` per step,
short-circuit to `wait` based on declared edges instead of list
position, evaluate every step every run). This was considered and
**explicitly rejected**: keeping steps a plain ordered list matters more
for table-column stability and for keeping test authoring simple than
correctly handling forks/joins does. The known consequence (a step that
doesn't really depend on its immediate predecessor still gets gated
behind it) is accepted as a guardrail that pushes authors toward
simpler, more linear workflows, not treated as a bug to fix later.

## Resolution of `python-library-notes.md`, item by item

- **0 (DAG/fork-join generalization):** Rejected — see above.
- **1 (two faces: function + CLI):** Superseded. There's no CLI face at
  all — `pytest` is the runner; a step is a plain decorated function
  called via `invoke()` inside an ordinary pytest test.
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
