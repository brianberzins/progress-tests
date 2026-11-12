import json
import os
import subprocess
import time
from datetime import datetime, timezone

from progress_tests import Status, invoke, step

PR_FIELDS = ",".join(
    [
        "author",
        "createdAt",
        "isDraft",
        "mergeable",
        "mergeStateStatus",
        "reviewDecision",
        "statusCheckRollup",
    ]
)
FAILED_CONCLUSIONS = {
    "FAILURE",
    "CANCELLED",
    "TIMED_OUT",
    "ACTION_REQUIRED",
    "STARTUP_FAILURE",
    "STALE",
}
FAILED_STATES = {"FAILURE", "ERROR"}
# GitHub computes a PR's mergeability only once it's asked for
MERGEABILITY_COMPUTE_SECONDS = 3


def gh_json(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr}")
    return json.loads(result.stdout)


def fetch_pr(url):
    pr = gh_json("pr", "view", url, "--json", PR_FIELDS)
    if pr["mergeable"] != "UNKNOWN":
        return pr
    time.sleep(MERGEABILITY_COMPUTE_SECONDS)
    return gh_json("pr", "view", url, "--json", PR_FIELDS)


@step("AGE")
def age(case) -> tuple[Status, dict]:
    try:
        pr = fetch_pr(case["name"])
    except RuntimeError:
        return Status.FAIL("gh error"), {}
    opened = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
    open_for = datetime.now(timezone.utc) - opened
    return Status.INFO(format_duration(open_for)), {"pr": pr}


def format_duration(duration):
    if duration.days:
        return f"{duration.days}d"
    if duration.seconds >= 3600:
        return f"{duration.seconds // 3600}h"
    return f"{duration.seconds // 60}m"


@step("AUTHOR")
def author(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    return Status.INFO(case["pr"]["author"]["login"])


@step("CI")
def ci(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    checks = case["pr"]["statusCheckRollup"]
    if not checks:
        return Status.INFO("no CI")
    failed = sum(
        1
        for c in checks
        if c.get("conclusion") in FAILED_CONCLUSIONS or c.get("state") in FAILED_STATES
    )
    done = sum(
        1
        for c in checks
        if c.get("status") == "COMPLETED"
        or c.get("state") in {"SUCCESS", *FAILED_STATES}
    )
    if failed:
        return Status.FAIL(f"{failed} failed")
    if done < len(checks):
        return Status.WAIT(f"{done}/{len(checks)}")
    return Status.PASS(f"{done}/{len(checks)}")


@step("CONFLICTS")
def conflicts(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    mergeable = case["pr"]["mergeable"]
    if mergeable == "CONFLICTING":
        return Status.FAIL("conflicts")
    if mergeable == "UNKNOWN":
        return Status.WAIT("unknown")
    return Status.PASS("none")


@step("DRAFT")
def draft(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    if case["pr"]["isDraft"]:
        return Status.WAIT("draft")
    return Status.PASS("ready")


@step("BEHIND")
def behind(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    merge_state = case["pr"]["mergeStateStatus"]
    if merge_state == "BEHIND":
        return Status.WAIT("behind")
    if merge_state == "UNKNOWN":
        return Status.WAIT("unknown")
    return Status.PASS("current")


@step("REVIEW")
def review(case) -> Status:
    if "pr" not in case:
        return Status.FAIL("no PR")
    decision = case["pr"]["reviewDecision"]
    if decision == "CHANGES_REQUESTED":
        return Status.FAIL("changes req")
    if decision == "REVIEW_REQUIRED":
        return Status.WAIT("needed")
    if decision == "APPROVED":
        return Status.PASS("approved")
    return Status.PASS("n/a")


def test_org_prs():
    org = os.environ["ORG"]
    prs = gh_json(
        "search",
        "prs",
        "--owner",
        org,
        "--state",
        "open",
        "--limit",
        "1000",
        "--json",
        "url",
        "--",
        "archived:false",
    )
    urls = sorted(pr["url"] for pr in prs)
    if not urls:
        print(f"no open PRs in {org}")
        return
    inputs = [{"name": url} for url in urls]
    steps = [age, author, ci, conflicts, draft, behind, review]
    invoke(steps, inputs, parallelism=10, show_details=False)
