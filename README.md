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
    return Status.PASS if condition_one(case["name"]) else Status.WAIT


@step("STEP_TWO")
def step_two(case) -> Status:
    return Status.PASS if condition_two(case["name"]) else Status.WAIT


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
each input, stopping at that input's first step that isn't
`Status.PASS`, and prints a color-coded table (one row per input, one
column per step) to stdout. By default, `Status.WAIT` doesn't fail the
test (it's the expected state for something still in progress);
`Status.FAIL` always does. Pass `fail_on_wait=True` to `invoke()` to
also fail on `Status.WAIT`.

A step can also return a value for later steps on the same input to
use, alongside its `Status`:

```python
@step("STEP_ONE")
def step_one(case) -> tuple[Status, dict]:
    return Status.PASS, {"example_key": "example_value"}


@step("STEP_TWO")
def step_two(case) -> Status:
    you_can_use = case["example_key"]
    return Status.PASS if condition_two(you_can_use) else Status.WAIT
```

If a step's returned value would overwrite an existing key — from the
original input, or a previous step — `invoke()` raises `ValueError`
rather than silently picking a value.

### Status messages

`Status.PASS`/`WAIT`/`FAIL` are the plain values, but each is also
callable to attach a short message, shown in the table cell in place
of the default `pass`/`wait`/`fail` word:

```python
@step("BACKUP")
def backup(case) -> Status:
    return Status.WAIT("waiting on nightly backup")
```

Keep messages short — they render inline in a fixed-width table
column, and a long one widens that column for every row. A `Status`
with a message still compares equal to the plain status of the same
kind (`Status.WAIT("...") == Status.WAIT`), so `fail_on_wait` and
similar checks are unaffected.

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
