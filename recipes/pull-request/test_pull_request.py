import functools
import json
import os
import subprocess
from urllib.parse import quote
from datetime import datetime, timezone

import pathspec
from progress_tests import Status, invoke, step

PR_FIELDS = "url,author,number,isDraft,state,mergeable,mergeStateStatus,createdAt,closedAt,mergeCommit,baseRefName,files,latestReviews,statusCheckRollup"
FAILED_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}
FAILED_RUN_CONCLUSIONS = {c.lower() for c in FAILED_CONCLUSIONS}
FAILED_STATES = {"FAILURE", "ERROR"}

THREADS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) { nodes { isResolved } }
    }
  }
}
"""

LAST_COMMIT_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      commits(last: 1) { nodes { commit { committedDate author { user { login } } } } }
    }
  }
}
"""

CLASSIC_PROTECTION_QUERY = """
query($owner: String!, $repo: String!, $ref: String!) {
  repository(owner: $owner, name: $repo) {
    ref(qualifiedName: $ref) {
      branchProtectionRule {
        requiresApprovingReviews requiredApprovingReviewCount requiresCodeOwnerReviews
        requireLastPushApproval dismissesStaleReviews requiresConversationResolution
      }
    }
  }
}
"""

CODEOWNERS_PATHS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout)


def owner_repo(case):
    return case["name"].removeprefix("https://github.com/").split("/")[:2]


@step("AGE")
def age(case):
    try:
        pr = gh_json("pr", "view", case["name"], "--json", PR_FIELDS)
    except subprocess.CalledProcessError:
        return Status.FAIL("no PR")
    opened = datetime.fromisoformat(pr["createdAt"])
    ended = datetime.fromisoformat(pr["closedAt"]) if pr["closedAt"] else datetime.now(timezone.utc)
    return Status.INFO(format_duration(ended - opened)), {"pr": pr}


@step("AUTHOR")
def author(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    return Status.INFO(case["pr"]["author"]["login"])


def format_duration(duration):
    if duration.days:
        return f"{duration.days}d"
    if duration.seconds >= 3600:
        return f"{duration.seconds // 3600}h"
    return f"{duration.seconds // 60}m"


def latest_per_check(rollup):
    latest = {}
    for check in sorted(rollup, key=lambda c: (c.get("startedAt") or "", c.get("completedAt") or "")):
        latest[(check.get("workflowName"), check.get("name") or check.get("context"))] = check
    return list(latest.values())


@step("CI")
def ci(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    checks = latest_per_check(case["pr"]["statusCheckRollup"])
    if not checks:
        return Status.INFO("no CI")
    failed = sum(1 for c in checks if c.get("conclusion") in FAILED_CONCLUSIONS or c.get("state") in FAILED_STATES)
    done = sum(1 for c in checks if c.get("status") == "COMPLETED" or c.get("state") in {"SUCCESS", *FAILED_STATES})
    if failed:
        return Status.FAIL(f"{failed} failed")
    if done < len(checks):
        return Status.WAIT(f"{done}/{len(checks)}")
    return Status.PASS(f"{done}/{len(checks)}")


@step("READY")
def ready(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    if case["pr"]["isDraft"]:
        return Status.WAIT("draft")
    return Status.PASS("ready")


@step("UP_TO_DATE")
def up_to_date(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    pr = case["pr"]
    if pr["mergeable"] == "CONFLICTING":
        return Status.FAIL("conflicts")
    if pr["mergeable"] == "UNKNOWN":
        return Status.WAIT("unknown")
    if pr["mergeStateStatus"] == "BEHIND":
        return Status.WAIT("behind")
    return Status.PASS("current")


@step("THREADS")
def threads(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    pr = case["pr"]
    owner, repo = owner_repo(case)
    data = gh_json("api", "graphql", "-f", f"query={THREADS_QUERY}", "-F", f"owner={owner}", "-F", f"repo={repo}", "-F", f"number={pr['number']}")
    nodes = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    resolved = sum(1 for t in nodes if t["isResolved"])
    if resolved < len(nodes) and review_rules(owner, repo, pr["baseRefName"])["resolution"]:
        return Status.WAIT(f"{resolved}/{len(nodes)}")
    return Status.PASS(f"{resolved}/{len(nodes)}")


@functools.cache
def review_rules(owner, repo, base):
    """What the base branch's rulesets and classic protection together require of a PR's reviews."""
    rulesets = gh_json("api", f"repos/{owner}/{repo}/rules/branches/{quote(base, safe='')}")
    pull_request_rules = [r["parameters"] for r in rulesets if r["type"] == "pull_request"]
    data = gh_json("api", "graphql", "-f", f"query={CLASSIC_PROTECTION_QUERY}", "-F", f"owner={owner}", "-F", f"repo={repo}", "-F", f"ref=refs/heads/{base}")
    classic = ((data["data"]["repository"]["ref"] or {}).get("branchProtectionRule")) or {}
    classic_count = classic.get("requiredApprovingReviewCount") or 0 if classic.get("requiresApprovingReviews") else 0
    return {
        "required": max([r["required_approving_review_count"] for r in pull_request_rules] + [classic_count]),
        "code_owner": any(r["require_code_owner_review"] for r in pull_request_rules) or bool(classic.get("requiresCodeOwnerReviews")),
        "after_last_push": any(r["require_last_push_approval"] or r["dismiss_stale_reviews_on_push"] for r in pull_request_rules)
        or bool(classic.get("requireLastPushApproval") or classic.get("dismissesStaleReviews")),
        "not_last_pusher": any(r["require_last_push_approval"] for r in pull_request_rules) or bool(classic.get("requireLastPushApproval")),
        "resolution": any(r.get("required_review_thread_resolution") for r in pull_request_rules) or bool(classic.get("requiresConversationResolution")),
    }


@functools.cache
def code_owner_rules(owner, repo, base):
    """CODEOWNERS on the base branch as (pattern, owners) pairs; the last pair matching a file decides its owners."""
    for path in CODEOWNERS_PATHS:
        lookup = subprocess.run(["gh", "api", f"repos/{owner}/{repo}/contents/{path}?ref={quote(base, safe='')}", "-H", "Accept: application/vnd.github.raw"], capture_output=True, text=True)
        if lookup.returncode == 0:
            break
    else:
        return []
    rules = []
    for line in lookup.stdout.splitlines():
        if fields := line.split("#", 1)[0].split():
            pattern, *owners = fields
            rules.append((pathspec.PathSpec.from_lines("gitwildmatch", [pattern]), owners))
    return rules


def file_owners(rules, path):
    owners = None
    for spec, candidates in rules:
        if spec.match_file(path):
            owners = candidates
    return owners or []


@functools.cache
def team_members(org, team):
    return frozenset(gh_json("api", "--paginate", f"orgs/{org}/teams/{team}/members", "-q", "[.[].login]"))


def owned_by(owner, login):
    if "/" in owner:
        org, team = owner.removeprefix("@").split("/", 1)
        return login in team_members(org, team)
    return owner.removeprefix("@").lower() == login.lower()


@step("APPROVED")
def approved(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    pr = case["pr"]
    if any(r["state"] == "CHANGES_REQUESTED" for r in pr["latestReviews"]):
        return Status.FAIL("changes req")
    owner, repo = owner_repo(case)
    rules = review_rules(owner, repo, pr["baseRefName"])
    approvers = valid_approvers(owner, repo, pr, rules)
    needs_owner = rules["code_owner"] and code_owner_missing(owner, repo, pr, approvers)
    required = max(rules["required"], 1 if needs_owner else 0)
    if len(approvers) >= required and not needs_owner:
        return Status.PASS(f"{len(approvers)}/{required}")
    return Status.WAIT(f"{len(approvers)}/{required}")


def valid_approvers(owner, repo, pr, rules):
    approvals = [r for r in pr["latestReviews"] if r["state"] == "APPROVED"]
    if not rules["after_last_push"] or not approvals:
        return {r["author"]["login"] for r in approvals}
    data = gh_json("api", "graphql", "-f", f"query={LAST_COMMIT_QUERY}", "-F", f"owner={owner}", "-F", f"repo={repo}", "-F", f"number={pr['number']}")
    last = data["data"]["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]
    pusher = (last["author"]["user"] or {}).get("login") if rules["not_last_pusher"] else None
    return {r["author"]["login"] for r in approvals if r["submittedAt"] > last["committedDate"] and r["author"]["login"] != pusher}


def code_owner_missing(owner, repo, pr, approvers):
    rules = code_owner_rules(owner, repo, pr["baseRefName"])
    for f in pr["files"]:
        owners = file_owners(rules, f["path"])
        if owners and not any(owned_by(o, a) for o in owners for a in approvers):
            return True
    return False


@step("MERGED")
def merged(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    state = case["pr"]["state"]
    if state == "MERGED":
        return Status.PASS("merged")
    if state == "CLOSED":
        return Status.FAIL("closed")
    return Status.WAIT("open")


@step("POST_MERGE")
def post_merge(case):
    if "pr" not in case:
        return Status.FAIL("no PR")
    pr = case["pr"]
    if pr["state"] == "CLOSED":
        return Status.INFO("closed")
    if pr["state"] != "MERGED":
        return Status.WAIT("not merged")
    owner, repo = owner_repo(case)
    runs = gh_json("api", f"repos/{owner}/{repo}/actions/runs?head_sha={pr['mergeCommit']['oid']}&event=push&per_page=100")["workflow_runs"]
    failed = [r for r in runs if r["conclusion"] in FAILED_RUN_CONCLUSIONS]
    latest = [latest_completed(owner, repo, pr["baseRefName"], r) for r in failed]
    newer = [l for r, l in zip(failed, latest) if l and l["created_at"] > r["created_at"]]
    if len(failed) > len(newer):
        return Status.FAIL(f"{len(failed) - len(newer)} failed")
    if any(l["conclusion"] in FAILED_RUN_CONCLUSIONS for l in newer):
        return Status.FAIL("stale, broken")
    done = sum(1 for r in runs if r["status"] == "completed")
    if done < len(runs):
        return Status.WAIT(f"{done}/{len(runs)}")
    if newer:
        return Status.PASS("stale, ok")
    return Status.PASS(f"{done}/{len(runs)}")


def latest_completed(owner, repo, branch, run):
    runs = gh_json("api", f"repos/{owner}/{repo}/actions/workflows/{run['workflow_id']}/runs?branch={branch}&event=push&status=completed&per_page=1")["workflow_runs"]
    return runs[0] if runs else None


STEPS = [age, author, ci, ready, up_to_date, threads, approved, merged, post_merge]


def test_pull_requests():
    urls = os.environ["PR_URLS"].split()
    if not urls:
        print("no PRs")
        return
    invoke(STEPS, [{"name": url} for url in urls], show_details=False)
