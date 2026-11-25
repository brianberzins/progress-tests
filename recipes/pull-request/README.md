# Pull requests

A progressive test of pull requests, one row per PR, checking each PR
against the steps in `pull-request.md`: the process one PR goes through
from being opened to being merged with its post-merge automation
passing, or closed. The process file says what each column checks and
why; `test_pull_request.py` is how.

`AGE` (how long the PR has been or was open) and `AUTHOR` are
information, not checks, shown uncolored.

## Running it

Needs [uv](https://docs.astral.sh/uv/) and the
[GitHub CLI](https://cli.github.com/), logged in with read access to
the PRs' repos. Copy `test_pull_request.py` into an empty directory, and
from there, with the PR URLs separated by spaces or newlines:

```bash
PR_URLS="<PR URL> <PR URL>" uvx --with pathspec --from git+https://github.com/brianberzins/progress-tests@v1.2.0 progress-tests .
```

## Choosing PRs

Which PRs to check isn't part of the test. Any list of URLs works; GitHub
search is the usual source. Some lists worth watching, each a single
command to put inside `PR_URLS="$(...)"`:

Your open PRs:

```bash
gh search prs --limit 1000 --json url -q '.[].url' -- author:@me is:open archived:false
```

Someone else's open PRs waiting on a review from you or a team you're on:

```bash
gh search prs --limit 1000 --json url -q '.[].url' -- review-requested:@me -author:@me is:open archived:false
```

Every open PR in an org:

```bash
gh search prs --limit 1000 --json url -q '.[].url' -- org:<org> is:open archived:false
```

Your merged or closed PRs whose branch hasn't been deleted:

```bash
gh api graphql --paginate -f query='query($q: String!, $endCursor: String) { search(query: $q, type: ISSUE, first: 100, after: $endCursor) { pageInfo { hasNextPage endCursor } nodes { ... on PullRequest { url headRef { name } } } } }' -f q='is:pr is:closed archived:false author:@me' --jq '.data.search.nodes[] | select(.headRef != null) | .url'
```

GitHub search returns at most 1,000 results, so a larger list leaves
some PRs out.

Each PR costs a few GitHub API calls per run, plus one lookup per base
branch for its review rules and CODEOWNERS, against a limit of 5,000
GraphQL points an hour shared with everything else using your `gh`
login.
