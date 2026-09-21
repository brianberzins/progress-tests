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
from progress_tests import step, Status, invoke


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
- For each input independently: walks `steps` in order, stopping at the
  first step that isn't `Status.PASS`. Steps after that point are not
  evaluated for that input and render as blank cells.
- Input row label is `input["name"]`, falling back to `input[{i}]`
  (by position) when `"name"` is absent.
- Renders one color-coded table to stdout: one row per input, one
  column per `STEP_NAME` in first-seen order, and ANSI coloring,
  column-aligned. Glyphs are plain ASCII (`+`/`!`/`X`) rather than the
  shared standard's `✓`/`!`/`✗` — those aren't reliably single-width
  across terminals/fonts despite looking that way in isolation (found
  by a real misaligned table, not a theoretical concern), so this
  library diverges from the standard's suggested glyphs on purpose.
- Color auto-detects and is **not configurable**: off if
  `sys.stdout.isatty()` is false, or `NO_COLOR`/`CI` env vars are set;
  on otherwise.
- Pass/fail policy, per input, based on the status where evaluation
  stopped:
  - `pass` — fine.
  - `wait` — does not fail the test, by default. This is the expected,
    common state for an in-progress migration.
  - `fail` — always fails the test, unconditionally.
  - `fail_on_wait=True` promotes `wait` to a failure too, for the one
    test that opts into it.
- `invoke()` raises when the test should fail; it has no exit-code logic
  of its own. The runner's own exit code (0 if everything passed, 1 if
  anything failed or raised) is the entire CI-integration story.
- No stderr `STEP_NAME:class` line output. This is an intentional
  divergence from `progressive-test-standard.md`'s shell-oriented
  contract — dropped, not carried forward, since this library owns a
  private practices standard rather than a community one.

## Explicitly out of scope for v1

- No built-in checks or log-format parsers (S3 access logs, CloudFront,
  ALB). Pure framework — bring your own (e.g. `boto3`) inside your own
  step functions.
- No CLI flags beyond an optional discovery path. No fixtures, no
  parametrize, no plugin system of any kind.
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
`progress-tests [path]` (`src/progress_tests/cli.py`, wired up via
`[project.scripts]`):

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
