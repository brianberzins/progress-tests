"""A one-off, runnable example of a 5-step progressive test.

Each input is a folder under ./files/, representing one instance moving
through a small file pipeline: a source file gets counted, copied,
summarized, and finally marked done. The five instances below are each
stopped at a different one of those five steps, so running this file
shows the whole spectrum of progress in a single table.

Run it with: uv run pytest -q -s example/test_pipeline.py

(-s so the table prints even though every input passes; -q so pytest
doesn't echo the filename inline before the table's own header line --
harmless, but it makes the header look misaligned with the rows below
it, which it isn't.)
"""

from pathlib import Path

from progress_tests import Status, invoke, step

FILES_DIR = Path(__file__).parent / "files"


@step("SOURCE_EXISTS")
def source_exists(case) -> Status:
    source = FILES_DIR / case["name"] / "source.txt"
    return Status.PASS if source.is_file() else Status.WAIT


@step("SOURCE_POPULATED")
def source_populated(case) -> tuple[Status, dict]:
    source = FILES_DIR / case["name"] / "source.txt"
    lines = source.read_text().splitlines()
    if not lines:
        return Status.WAIT, {}
    return Status.PASS, {"line_count": len(lines)}


@step("COPY_MATCHES_SOURCE")
def copy_matches_source(case) -> Status:
    copy = FILES_DIR / case["name"] / "copy.txt"
    if not copy.is_file():
        return Status.WAIT
    you_can_use = case["line_count"]
    return (
        Status.PASS
        if len(copy.read_text().splitlines()) == you_can_use
        else Status.WAIT
    )


@step("SUMMARY_EXISTS")
def summary_exists(case) -> Status:
    summary = FILES_DIR / case["name"] / "summary.txt"
    return Status.PASS if summary.is_file() else Status.WAIT


@step("MARKED_DONE")
def marked_done(case) -> Status:
    marker = FILES_DIR / case["name"] / "DONE"
    return Status.PASS if marker.is_file() else Status.WAIT


def test_pipeline():
    steps = [
        source_exists,
        source_populated,
        copy_matches_source,
        summary_exists,
        marked_done,
    ]
    inputs = [
        {"name": "waiting-on-source"},
        {"name": "waiting-on-count"},
        {"name": "waiting-on-copy"},
        {"name": "waiting-on-summary"},
        {"name": "complete"},
    ]
    invoke(steps, inputs)
