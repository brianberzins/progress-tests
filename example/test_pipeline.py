from pathlib import Path

from progress_tests import Status, invoke, step

FILES_DIR = Path(__file__).parent / "files"
MIN_VERSION = 2


def _fields(name: str) -> dict[str, str]:
    path = FILES_DIR / f"{name}.txt"
    if not path.is_file():
        return {}
    fields = {}
    for line in path.read_text().splitlines():
        key, _, value = line.partition("=")
        fields[key] = value
    return fields


@step("FILE")
def file_exists(case) -> Status:
    path = FILES_DIR / f"{case['name']}.txt"
    return Status.PASS("found") if path.is_file() else Status.WAIT("missing")


@step("VERSION")
def version_parsed(case) -> tuple[Status, dict]:
    version = _fields(case["name"]).get("version")
    if version is None:
        return Status.WAIT("missing"), {}
    return Status.PASS(f"v{version}"), {"version": int(version)}


@step("UPGRADED")
def version_upgraded(case) -> Status:
    if "version" not in case:
        return Status.WAIT("no version")
    version = case["version"]
    if version < MIN_VERSION:
        return Status.WAIT(f"v{version}")
    return Status.PASS(f"v{version}")


@step("ROLLED_OUT")
def instances_rolled_out(case) -> Status:
    instances = _fields(case["name"]).get("instances")
    if instances is None:
        return Status.WAIT("missing")
    versions = [int(v) for v in instances.split(",")]
    lagging = [i for i, v in enumerate(versions) if v < MIN_VERSION]
    rolled_out = f"{len(versions) - len(lagging)}/{len(versions)}"
    if lagging:
        detail = "".join(
            f"instance {i}: v{versions[i]}, want v{MIN_VERSION}+\n" for i in lagging
        )
        return Status.WAIT(rolled_out, detail=detail)
    return Status.PASS(rolled_out)


@step("HEALTHY")
def is_healthy(case) -> Status:
    healthy = _fields(case["name"]).get("healthy")
    if healthy is None:
        return Status.WAIT("missing")
    return Status.PASS("healthy") if healthy == "true" else Status.WAIT("unhealthy")


def test_pipeline():
    steps = [
        file_exists,
        version_parsed,
        version_upgraded,
        instances_rolled_out,
        is_healthy,
    ]
    inputs = [
        {"name": "not-started"},
        {"name": "below-minimum"},
        {"name": "rolling-out"},
        {"name": "complete"},
    ]
    invoke(steps, inputs)
