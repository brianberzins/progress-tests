# Open PRs in an org

A progressive test of every open pull request in a GitHub org or user's
unarchived repos, for working the list down to zero. One row per PR:

- `AGE` and `AUTHOR`: information, not checks, shown uncolored. `AGE`
  also fetches the PR that every later step reads, and shows
  `FAIL gh error` when it can't.
- `CI`: completed checks out of all checks; `FAIL` if any failed.
- `CONFLICTS`: `FAIL` on merge conflicts.
- `DRAFT`: `WAIT` while the PR is a draft.
- `BEHIND`: `WAIT` while the branch is behind its base.
- `REVIEW`: the PR's review decision; `n/a` where review isn't required.

`CONFLICTS` and `BEHIND` show `WAIT unknown` while GitHub is still
computing mergeability, usually just after the base branch moves.

When the org has no open PRs, it prints that instead of a table. GitHub
search returns at most 1,000 PRs, so a larger org's table leaves some
out.

## Running it

Needs [uv](https://docs.astral.sh/uv/) and the
[GitHub CLI](https://cli.github.com/), logged in with access to the org.
Copy `test_org_prs.py` into an empty directory, and from there:

```bash
ORG=<org> uvx --from git+https://github.com/brianberzins/progress-tests@v1.2.0 progress-tests .
```

To rerun it every 5 minutes:

```bash
while true; do out="$(ORG=<org> uvx --from git+https://github.com/brianberzins/progress-tests@v1.2.0 progress-tests . 2>&1)"; clear; echo "$out"; sleep 300; done
```

A plain loop rather than `watch` keeps long rows from being cut off at
the terminal's width, which also keeps each PR's URL clickable in
terminals that link URLs.

Each run makes one GitHub GraphQL call per PR, against a limit of
5,000 points an hour shared with everything else using your `gh`
login. With a few hundred open PRs, lengthen the `sleep` to stay under
it.
