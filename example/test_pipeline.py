from pathlib import Path

from progress_tests import Status, invoke, step

FILES_DIR = Path(__file__).parent / "files"


@step("SOURCE")
def source_exists(case) -> Status:
    source = FILES_DIR / case["name"] / "source.txt"
    return Status.PASS("found") if source.is_file() else Status.WAIT("missing")


@step("POPULATED")
def source_populated(case) -> tuple[Status, dict]:
    source = FILES_DIR / case["name"] / "source.txt"
    lines = source.read_text().splitlines()
    if not lines:
        return Status.WAIT("empty"), {}
    return Status.PASS("ready"), {"line_count": len(lines)}


@step("COPY")
def copy_matches_source(case) -> Status:
    copy = FILES_DIR / case["name"] / "copy.txt"
    if not copy.is_file():
        return Status.WAIT("missing")
    expected_lines = case["line_count"]
    copy_line_count = len(copy.read_text().splitlines())
    if copy_line_count != expected_lines:
        return Status.WAIT(f"{copy_line_count}/{expected_lines}")
    return Status.PASS(f"{copy_line_count}/{expected_lines}")


@step("SUMMARY")
def summary_exists(case) -> Status:
    summary = FILES_DIR / case["name"] / "summary.txt"
    return Status.PASS("found") if summary.is_file() else Status.WAIT("missing")


@step("DONE")
def marked_done(case) -> Status:
    marker = FILES_DIR / case["name"] / "DONE"
    return Status.PASS("done") if marker.is_file() else Status.WAIT("pending")


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
        {"name": "partial-copy"},
        {"name": "waiting-on-summary"},
        {"name": "complete"},
    ]
    invoke(steps, inputs)
