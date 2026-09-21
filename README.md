# progress-tests

A library for writing progressive tests: ordered, deterministic checks
that track and document real-world progress toward a desired state
(e.g. a migration, a phased rollout). A fully-passing progressive test
is a long-lived test of the final desired state, not a disposable
migration artifact.

See `docs/design/progress-tests-library.md` for the full design and
`docs/LANGUAGE.md` for terminology.

## Usage

```python
from progress_tests import Status, invoke, step


@step("STEP_ONE")
def step_one(case) -> Status:
    if condition_one(case["name"]):
        return Status.PASS("ok")
    return Status.WAIT("waiting")


@step("STEP_TWO")
def step_two(case) -> Status:
    if condition_two(case["name"]):
        return Status.PASS("ok")
    return Status.WAIT("waiting")


def test_migration():
    steps = [step_one, step_two]
    inputs = [
        {"name": "instance-a"},
        {"name": "instance-b"},
    ]
    invoke(steps, inputs)
```

Run it with the bundled runner: `progress-tests [path]` (`path`
defaults to the current directory). It walks `path` for
`test_*.py`/`*_test.py` files, imports them, and calls every top-level
`test_*` function it finds with no arguments — no fixtures, no
parametrize, no plugin system. `invoke()` runs `steps` in order for
each input, stopping at that input's first step that isn't a `PASS`,
and prints a color-coded table (one row per input, one column per
step) to stdout. By default, `WAIT` doesn't fail the test (it's the
expected state for something still in progress); `FAIL` always does.
Pass `fail_on_wait=True` to `invoke()` to also fail on `WAIT`.

A step can also return a value for later steps on the same input to
use, alongside its `Status`:

```python
@step("STEP_ONE")
def step_one(case) -> tuple[Status, dict]:
    return Status.PASS("ok"), {"example_key": "example_value"}


@step("STEP_TWO")
def step_two(case) -> Status:
    you_can_use = case["example_key"]
    if condition_two(you_can_use):
        return Status.PASS("ok")
    return Status.WAIT("waiting")
```

If a step's returned value would overwrite an existing key — from the
original input, or a previous step — `invoke()` raises `ValueError`
rather than silently picking a value.

### Message guidance

`Status.PASS`/`WAIT`/`FAIL` each take an optional message, shown in
that cell of the table: `Status.WAIT("no backup")` renders as `! no
backup`. Leave it out (`Status.PASS()`) and the cell just shows the
glyph. Keep it short — aim for well under 12 characters. It renders
inline in a fixed-width table column, and a long one widens that
column for every row.

Two `Status`es are equal only when both their kind and message
match — `Status.FAIL("boom") != Status.FAIL("other")` — so don't
compare a step's result against a specific `Status` value in your own
code unless you mean that exact message too.

`@step` automatically attaches a message when a step function raises:
`"assert fail"` for an `AssertionError`, `"exception"` for anything
else. Either way, the full traceback isn't lost — it prints once,
after the whole table, rather than interleaved with it.

## Dependencies

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) for dependency management and
  running commands (`uv sync`, `uv run pytest`, `uv run ruff check .`)

## Deployment

Not published anywhere (no PyPI, no GitHub releases). Install directly
from this repository if you need it elsewhere.
