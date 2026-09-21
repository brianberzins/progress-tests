# progressive-tests

A library for writing progressive tests: ordered, deterministic checks
that track and document real-world progress toward a desired state
(e.g. a migration, a phased rollout). A fully-passing progressive test
is a long-lived test of the final desired state, not a disposable
migration artifact.

See `docs/design/progressive-tests-library.md` for the full design and
`docs/LANGUAGE.md` for terminology.

## Usage

```python
from progressive_tests import Status, invoke, step


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
    invoke(steps, inputs)
```

Run it like any other pytest test: `pytest`. `invoke()` runs `steps` in
order for each input, stopping at that input's first step that isn't
`Status.PASS`, and prints a color-coded table (one row per input, one
column per step) to stdout. By default, `Status.WAIT` doesn't fail the
test (it's the expected state for something still in progress);
`Status.FAIL` always does. Pass `fail_on_wait=True` to `invoke()` to
also fail on `Status.WAIT`.

A step can also return data for later steps on the same input, e.g. to
carry a resource ID created by an earlier step:

```python
@step("DISTRIBUTION_CREATED")
def distribution_created(case) -> Status:
    return Status.PASS, {"distribution_id": create_distribution(case["bucket"])}


@step("DISTRIBUTION_DEPLOYED")
def distribution_deployed(case) -> Status:
    return Status.PASS if is_deployed(case["distribution_id"]) else Status.WAIT
```

If a step's returned data would overwrite an existing key — from the
original input, or a previous step — `invoke()` raises `ValueError`
rather than silently picking a value.

## Dependencies

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) for dependency management and
  running commands (`uv sync`, `uv run pytest`, `uv run ruff check .`)

## Deployment

Not published anywhere (no PyPI, no GitHub releases). Install directly
from this repository if you need it elsewhere.
