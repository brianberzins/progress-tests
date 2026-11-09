# Open PRs in an org

A progressive test of every open pull request in a GitHub org or user's
unarchived repos, for working the list down to zero. One row per PR:

- `AGE` and `AUTHOR`: always `PASS`, for reading the table.
- `CI`: completed checks out of all checks; `FAIL` if any failed.
- `READY`: `FAIL` on merge conflicts, `WAIT` for a draft or a branch
  behind its base.
- `REVIEW`: the PR's review decision; `n/a` where review isn't required.

When the org has no open PRs, it prints that instead of a table.

## Running it

Needs [uv](https://docs.astral.sh/uv/) and the
[GitHub CLI](https://cli.github.com/), logged in with access to the org.
From a directory holding `test_org_prs.py`:

```bash
ORG=<org> uvx --from git+https://github.com/brianberzins/progress-tests@v1.1.0 progress-tests .
```

To rerun it every 5 minutes:

```bash
while true; do out="$(ORG=<org> uvx --from git+https://github.com/brianberzins/progress-tests@v1.1.0 progress-tests . 2>&1)"; clear; echo "$out"; sleep 300; done
```

A plain loop rather than `watch` keeps long rows from being cut off at
the terminal's width, which also keeps each PR's URL clickable in
terminals that link URLs.
