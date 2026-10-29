# Run Claude Code in Modal Sandboxes: GitHub Issue to Pull Request

A hands-on walkthrough of [Fife](https://github.com/mathaix/fife), an open-source agent factory. By the end you
will have labelled a GitHub issue and received a pull request, written by Claude Code inside a Modal Sandbox,
with its tests run by the orchestrator before you ever see it. Budget about 15 minutes, most of it waiting
for the first image build.

The ideas behind it are in the talk
[Build Your Software Agent Factory](https://presentations.claramap.com/agentsandboxes/)
([transcript](https://presentations.claramap.com/agentsandboxes/transcript/)). This page is the
practical half: commands, what you should see, and what to do when you don't.

## What you are building

```
label an issue `agent`
        │
        ▼
orchestrator (your laptop) ──clone──▶ Modal Sandbox ──claude -p──▶ Claude
   polls GitHub every 5 s             runs the agent, then verify.sh, up to 3 rounds
        │                                     │
        ▼                                     ▼
pull request on agent/issue-N  ◀──diff──  sandbox terminated
```

Three parts. The **orchestrator** (`agent/run.py`) runs wherever you start it and holds your GitHub token.
**Modal** gives every issue a fresh sandbox from a cached image with Claude Code installed. **Claude Code**
runs headless (`claude -p`) inside the sandbox with only the model credential. The sandbox never sees your
GitHub token and can only reach `api.anthropic.com`, the package registries and a few CDNs.

## Prerequisites

- Python 3 and [uv](https://docs.astral.sh/uv/)
- A [Modal](https://modal.com) account (the free tier is enough for this)
- A GitHub fine-grained personal access token
- A Claude Pro or Max subscription, or an Anthropic API key
- The [GitHub CLI](https://cli.github.com) (`gh`), only for the commands below that create a repo

## 1. Install

```bash
git clone https://github.com/mathaix/fife.git && cd fife
make setup              # creates .venv with uv
.venv/bin/modal setup   # opens the browser to log in to Modal
```

`make` on its own lists every command.

## 2. Credentials

Create a fine-grained token at <https://github.com/settings/personal-access-tokens/new>. Give it access to
the repositories you want agents to work on, with these repository permissions:

| Permission | Access |
|---|---|
| Contents | Read and write |
| Issues | Read and write |
| Pull requests | Read and write |
| Workflows | leave off |

The token's repository access *is* the agents' scope: `make watch` works every repo it can push to.

Copy `.env.example` to `.env` and set the token:

```
GH_DEMO_TOKEN=github_pat_...
```

For Claude, do nothing yet. On first run the orchestrator notices there is no credential, runs
`claude setup-token`, opens the browser for you to log in, and caches the subscription token in `.env`.
If you would rather use the API, set `ANTHROPIC_API_KEY` instead.

## 3. Give the agents a repository

Fife ships `sample_app/`, a small FastAPI bookshelf with three seeded bugs. Push it to a repository of its
own that your token can reach:

```bash
gh repo create bookshelf --private --clone
cp -r sample_app/app sample_app/requirements.txt bookshelf/
mkdir bookshelf/tests && cp sample_app/tests/test_books.py bookshelf/tests/
git -C bookshelf add . && git -C bookshelf commit -qm "Bookshelf sample app" && git -C bookshelf push -q
```

Then create the demo issues and the four labels Fife uses (`agent`, `agent-working`, `agent-done`,
`agent-failed`):

```bash
.venv/bin/python agent/seed_issues.py --repo <you>/bookshelf
```

You should see three issue numbers printed, for pagination, a health endpoint and input validation.

Using your own repository instead? Any repo works. Create the `agent` label once, and add a `CLAUDE.md` at the
root telling the agent how to run the tests. Claude Code reads it automatically.

## 4. Run one issue

```bash
make issue ISSUE=<you>/bookshelf#1
```

What happens, in order:

1. The issue is relabelled `agent-working` and gets a run-record comment.
2. The first run builds the Modal image (Python, git, ffmpeg, Playwright with Chromium, Claude Code). This
   takes a few minutes once; Modal caches it.
3. A sandbox starts and the clone is uploaded. The sandbox id is printed; you can watch it in the Modal
   dashboard under the `fife` app.
4. Claude Code's steps stream to your terminal: reading files, editing, running tests, writing
   `/tmp/agent/verify.sh`.
5. The orchestrator runs `verify.sh` itself. On failure the output goes back to the same Claude session and
   it tries again, up to three rounds.
6. The diff is pulled out, committed to `agent/issue-1`, pushed, and a PR opens. The sandbox is terminated.

Expect one to five minutes for a sample-app issue after the image is cached.

## 5. Review the pull request

The PR closes the issue and contains the agent's summary, a line like

```
**Verified** in the sandbox, round 1 of 3: 5 passed, 1 warning in 0.42s
```

the `verify.sh` the agent wrote, and, when the change has a web page, a GIF of the Playwright test that
exercised it. The issue is labelled `agent-done`. Merge it like any other PR, or don't: agents never merge.

Not happy with it? Comment on the PR or the issue:

```
/agent Use a 422 instead of a 400 and add a test for the boundary year
```

The orchestrator (if `make watch` is running) starts a new sandbox, resumes the saved Claude session, and
pushes to the same branch so the PR updates.

## 6. Run the whole backlog

```bash
make watch
```

Now label any issue `agent` in any repo the token can push to. Each one gets its own sandbox and they run in
parallel. Ten labels, ten sandboxes. On a subscription token they share your plan's usage limits, so start
with two or three.

## Troubleshooting

**`No valid Claude subscription token in .env: running claude setup-token`** on first run. Expected. Log in
in the browser; the token is saved to `.env`. If no browser opens, run `.venv/bin/claude setup-token`
by hand, or run `claude setup-token` with any Claude Code install, and paste the result into `.env` as
`CLAUDE_CODE_OAUTH_TOKEN=...`.

**Nothing happens after labelling.** The watcher only sees repos the token can push to, skips archived
repos, and only looks at open issues labelled exactly `agent`. Check the terminal: it prints the repos it is
watching. The label must exist in that repo; `seed_issues.py` creates it, for other repos create it in the
GitHub UI.

**`Still failing after 3 rounds`.** The agent could not make its own verify script pass. The last output is
in the run-record comment on the issue. Usually the issue text was ambiguous or the repo needs a `CLAUDE.md`
that says how to run the tests. Fix the issue text, then re-add the `agent` label to retry.

**`The agent made no changes.`** The agent decided nothing was needed, or only wrote files outside the repo.
Read its summary in the run record; sharpen the issue.

**`Refusing to push changes to CI/submodule config`.** The agent edited `.github/`. Fife never pushes that,
since workflows run with the repo's secrets. The dropped diff is shown in the PR for you to apply by hand.

**`git push` failed.** The verified diff is attached to the issue as a comment and kept in the Modal Volume
`agent-sessions`, so the work is not lost. Check the token's Contents permission for that repo, then re-add
the label or comment `/agent continue`.

**Dependency install fails inside the sandbox.** Egress is limited to PyPI, npm, and the jsDelivr, unpkg
and cdnjs CDNs. A build that fetches from elsewhere (a private index, GitHub releases) will fail. Add the
host to `EGRESS` in `agent/run.py`.

**Sandbox timed out.** Each sandbox has a one-hour lifetime and each verify run a 15-minute limit. Long test
suites need a `CLAUDE.md` that points the agent at the fast subset.

**Where did the session go?** Claude sessions are saved to the Modal Volume `agent-sessions` as
`<owner>/<repo>/issue-N/<session-id>.jsonl`, never to GitHub. `modal volume ls agent-sessions` lists them.

## Where to go next

- [Fife on GitHub](https://github.com/mathaix/fife): the orchestrator is one file, `agent/run.py`, about 500 lines.
- [Architecture walkthrough](architecture.md): the per-issue sequence, credential boundaries and failure paths.
- [The talk](https://presentations.claramap.com/agentsandboxes/): why sandboxes plus headless agents is the
  step that turns steering into managing.
- [Modal Sandboxes docs](https://modal.com/docs/guide/sandbox) and
  [Claude Code headless mode](https://docs.claude.com/en/docs/claude-code/headless).
