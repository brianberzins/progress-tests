"""A one-off, runnable example of a 5-step progressive test.

Each input is a folder under ./files/, representing one instance moving
through a small file pipeline: a source file gets counted, copied,
summarized, and finally marked done. The five instances below are each
stopped at a different one of those five steps, so running this file
shows the whole spectrum of progress in a single table. It also shows
`Status` messages in both directions: a `WAIT` explaining what it's
waiting on, and a `PASS` reporting something about what it found.

Run it with: uv run progress-tests example
"""

from pathlib import Path

from progress_tests import Status, invoke, step

FILES_DIR = Path(__file__).parent / "files"


@step("SOURCE")
def source_exists(case) -> Status:
    source = FILES_DIR / case["name"] / "source.txt"
    return Status.PASS if source.is_file() else Status.WAIT("no source file")


@step("POPULATED")
def source_populated(case) -> tuple[Status, dict]:
    source = FILES_DIR / case["name"] / "source.txt"
    lines = source.read_text().splitlines()
    if not lines:
        return Status.WAIT("source file is empty"), {}
    return Status.PASS(f"{len(lines)} lines"), {"line_count": len(lines)}


@step("COPY")
def copy_matches_source(case) -> Status:
    copy = FILES_DIR / case["name"] / "copy.txt"
    if not copy.is_file():
        return Status.WAIT("no copy yet")
    you_can_use = case["line_count"]
    copy_line_count = len(copy.read_text().splitlines())
    if copy_line_count != you_can_use:
        return Status.WAIT(f"copy has {copy_line_count}, want {you_can_use}")
    return Status.PASS


@step("SUMMARY")
def summary_exists(case) -> Status:
    summary = FILES_DIR / case["name"] / "summary.txt"
    return Status.PASS if summary.is_file() else Status.WAIT("no summary yet")


@step("DONE")
def marked_done(case) -> Status:
    marker = FILES_DIR / case["name"] / "DONE"
    return Status.PASS if marker.is_file() else Status.WAIT("not marked done")


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
