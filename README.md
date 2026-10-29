<p align="center">
  <img src="docs/logo.svg" alt="Fife logo: a golden retriever face next to the words Fife, Your AI backlog resolver" width="640">
</p>

# Fife — Claude Code Agent Factory on Modal Sandboxes

**Your AI backlog resolver.** Stop steering coding agents. Start managing them.

![From chatting with an assistant, to one agent in a terminal, to parallel local agents, to the discovery of fire: sandboxes plus headless agents make the agent factory, where tickets go in and pull requests come out.](docs/evolution.png)

**TL;DR:** the two concepts you need to build your own agent factory are **headless agent execution** and
**sandboxes**. Fife is a reference implementation that shows how this is done.

Working with coding agents for most of us means sitting with them: one session, one prompt at a time, watching and
correcting. You can only steer one agent at once, so you're the bottleneck.

Fife lets you manage your agents instead. Hand off work the way you would to a team: write a clear issue
and label it. Agents pick it up, each on its own disposable cloud computer, and come back with finished pull
requests that are tested and show that the change works. You review results, not sessions.

[**Presentation: Build Your Software Agent Factory →**](https://presentations.claramap.com/agentsandboxes/)

Learn how Modal Sandboxes and headless Claude Code turn
GitHub issues into tested pull requests.

[Read the transcript](https://presentations.claramap.com/agentsandboxes/transcript/)

## Background

Fife demonstrates how to build a software factory with [Modal](https://modal.com) as the agent runtime and headless
Claude Code as the coding agent. Your Claude subscription token is injected into each sandbox, so the agents
run on your subscription.

**TL;DR:** to build your own software factory you need two ideas:

1. **Agent sandboxes.** A disposable, isolated computer per task, so an agent can run anything without
   touching your machine. Fife creates a fresh [Modal](https://modal.com) sandbox per issue.
2. **Headless agent execution** (e.g. `claude -p`). The agent runs from a script with no one at the keyboard,
   so issues, cron jobs or webhooks can start it. Fife runs `claude -p` inside each sandbox.

Put the two together and every ticket becomes its own agent run, in parallel, with a pull request at the end.

## Why it's useful

- **Your backlog becomes work in progress.** The small fixes, docs gaps and missing tests nobody gets to are
  each one label away from a pull request.
- **Parallel by default.** Ten labelled issues means ten agents working at once, each in its own sandbox.
- **Proof, not promises.** A PR only appears once its tests pass, and web changes come with a recording of
  the passing run, so reviewing is quick.
- **Anyone can delegate.** If you can write a clear issue, you can hand off a change; an engineer reviews it.
- **You stay in control.** Agents never merge, never see your GitHub token and can't change CI config.
  Every change arrives as a PR you approve.
- **Your repos, your accounts.** No app to install or service to grant access. The orchestrator runs anywhere
  with your GitHub token and your Claude subscription.

> Agents follow the instructions in issue text. Use it on repos where you trust who can file and label issues.

## Quickstart

Five minutes from clone to a pull request, using the bundled sample app.

**Prerequisites:** Python 3 and [uv](https://docs.astral.sh/uv/); a [Modal](https://modal.com) account;
a GitHub fine-grained token; a Claude Pro/Max subscription (or an Anthropic API key).

**1. Clone and install.**

```bash
git clone https://github.com/mathaix/fife.git && cd fife
make setup                      # creates .venv; `make` lists all commands
.venv/bin/modal setup           # log in to Modal (or export MODAL_TOKEN_ID / MODAL_TOKEN_SECRET)
```

**2. Credentials.** Put these in a `.env` file in this folder (gitignored), one `KEY=value` per line, or export
them in your shell (the shell wins). Full-line `#` comments are fine; inline comments are not.

```
GH_DEMO_TOKEN=github_pat_...
```

| Variable | What |
|---|---|
| `GH_DEMO_TOKEN` | Fine-grained GitHub token. Agents watch every repo this token can push to, so its repository access *is* their scope. Permissions: Contents, Issues, Pull requests (read/write); leave Workflows off |
| `CLAUDE_CODE_OAUTH_TOKEN` | From `claude setup-token`; runs on your Claude Pro/Max subscription. Or set `ANTHROPIC_API_KEY` instead. If neither is set, `run.py` runs `claude setup-token` for you and caches the token in `.env` (gitignored) until it expires |
| `AGENT_MODEL` | Optional, defaults to `sonnet` |

**3. Give the agents a repo.** `sample_app/` is a small FastAPI bookshelf with three seeded bugs. Push it to a repo
of its own that the token can push to, and create the three demo issues there:

```bash
gh repo create bookshelf --private --clone
cp -r sample_app/app sample_app/requirements.txt bookshelf/
mkdir bookshelf/tests && cp sample_app/tests/test_books.py bookshelf/tests/
git -C bookshelf add . && git -C bookshelf commit -qm "Bookshelf sample app" && git -C bookshelf push -q
.venv/bin/python agent/seed_issues.py --repo <you>/bookshelf    # prints #1 #2 #3 (add --reset between rehearsals)
```

**4. Run one issue.**

```bash
make issue ISSUE=<you>/bookshelf#1
```

The terminal streams the agent's steps while a sandbox appears in the Modal dashboard.

**5. The pull request.** A few minutes later the issue is labelled `agent-done` and a PR titled
`Fix #1: ...` arrives on branch `agent/issue-1`. It closes the issue, summarises the change, shows the
verify output from the sandbox (`**Verified** in the sandbox, round 1 of 3: 5 passed`), includes the test
script the agent wrote, and, for web changes, a GIF of the passing browser test.
[Here is one](https://github.com/mathaix/fife/pull/5). Review and merge it like any other PR.

Longer walkthrough with troubleshooting: [docs/tutorial.md](docs/tutorial.md).

## Using it

```bash
make watch                      # every repo the token can push to
make issue ISSUE=owner/name#3   # one issue, e.g. to retry a failed one
```

Then label any issue `agent` (create the label in the repo the first time), and review the PR when it
arrives. A failed issue isn't retried while `--watch` keeps running; restart it, or use `make issue`.

Give agents per-repo guidance (how to run the tests, code style) in a `CLAUDE.md` at the target repo's root,
which Claude Code reads automatically. On a subscription token, parallel agents share your plan's usage limits.

## Workflow

![Workflow: create an issue and label it agent; the orchestrator polls GitHub every five seconds, dispatches a Modal sandbox, verifies the result and publishes a PR with a preview.](docs/laptop-workflow.svg)

1. **Start up.** `python agent/run.py --watch`. If no Claude credential is set and `.env` has no valid
   subscription token, it runs `claude setup-token` (you log in in the browser) and saves the token to `.env`.
2. **Watch.** Every minute it asks GitHub which repos the token can push to (skipping archived repos and
   repos with no open issues). Every 5 seconds it checks those repos for open issues labelled `agent`.
3. **Pick up.** For each new labelled issue: relabel it `agent-working`, comment "Picked up", and clone the
   issue's repo with the token. Several issues run at once, each independently.
4. **Sandbox.** Create a Modal sandbox and upload the clone into it. The sandbox gets the Claude credential
   only, never the GitHub token, and can reach only `api.anthropic.com`, the PyPI/npm registries and the
   jsDelivr/unpkg/cdnjs CDNs (so web pages render in browser tests).
5. **Agent.** Claude Code gets the issue text and is told to: make the change; add tests next to the existing
   ones (for a web app, an end-to-end Playwright browser test that records a video and screenshots when
   `DEMO_DIR` is set); and write `/tmp/agent/verify.sh`, a script that runs the whole test suite. It doesn't
   commit. Its steps stream to the orchestrator's terminal.
6. **Verify, in the same sandbox.** The orchestrator runs `verify.sh` itself rather than trusting the agent's
   word. If it fails, the output goes back to the same Claude session ("this failed, fix it"), and the check
   runs again, up to 3 rounds; after that the issue is marked failed with the last output.
7. **Check the change, outside the sandbox.** Pull the diff out, apply it to the orchestrator's clone, and
   refuse to continue if it touches `.github/` (workflows run with the repo's secrets).
8. **Publish.** Commit to branch `agent/issue-N` and push. If the passing run recorded anything, turn the
   video into a GIF (GitHub plays those inline), take only genuine PNG/GIF files under 5 MB, and push them to
   a separate branch `agent-media-issue-N`, so they show in the PR without being part of its changes. Open
   a PR that says "Closes #N" with the agent's summary, the verify result and script, and the demo images;
   comment the link on the issue.
9. **Record and shut down.** The sandbox is terminated. Every run, success or failure, posts or updates one run-record comment on the issue (status,
   failed stage, reason, verify rounds, cost, sandbox id) and relabels it `agent-done` or `agent-failed`. The
   Claude session file is copied into the Modal Volume `agent-sessions` as `<repo>/issue-N/<session-id>.jsonl`
   (never to GitHub, since it can hold private code). If the push fails after a few retries, the verified diff
   is attached to the issue and saved in the Volume.
10. **Retry or steer.** Re-adding `agent` retries without restarting the watcher. A comment starting with
    `/agent <instructions>` on the issue or its PR, from an owner, member or collaborator, starts a new run on
    the same `agent/issue-N` branch (or applies the kept diff if the push never happened), resuming the saved
    session; if that is missing or too big it starts a fresh session from the issue, PR description and diff.
    Runs on one issue queue up one after another. Ordinary comments never trigger a run.

## Architecture

![Architecture: Python creates a Modal sandbox from an image with Claude Code installed, starts the coding agent, reruns tests, and publishes a PR.](docs/architecture.svg)

There are three parts:

- **The orchestrator** (`agent/run.py`) runs wherever you start it, on your machine or a server.
  It holds the GitHub token, talks to GitHub, and decides what happens next.
- **Modal** gives each issue a fresh, throwaway sandbox from a reusable image with Claude Code installed.
- **Claude** (the model) runs on Anthropic's servers.

**The orchestrator runs the job; Claude Code does the coding inside the sandbox.**

- **Safety:** the agent runs arbitrary commands with permissions skipped, which is fine because the
  sandbox is the boundary. It only holds the model credential; the GitHub token never enters it.
- **Speed:** each issue gets a ready-to-go environment in seconds.
- **Scale:** label three issues and three sandboxes work in parallel.

See [the architecture walkthrough and sequence diagram](docs/architecture.md) for the image build,
per-issue lifecycle, credential boundaries and failure path, or download
[the interactive workflow diagram](docs/laptop-workflow.html) and open it locally to explore each step.

## Repository layout

| Path | What's there |
|---|---|
| `agent/` | The backlog resolver: the orchestrator (`run.py`), its testable logic (`runs.py`: run records, `/agent` parsing, dispatch), the GitHub client (`gh.py`) and the demo issue seeder (`seed_issues.py`) |
| `sample_app/` | A small FastAPI bookshelf app to try it on, with its pytest suite |
| `docs/` | Tutorial, architecture walkthrough, diagrams, the interactive workflow page and the social preview image |
| `Makefile` | Shortcuts: `make setup`, `make watch`, `make issue`, `make seed` |
| `PRD.md` | Product requirements |

## Running the tests

The sample app's tests cover the endpoints agents change. They also check that the README and
docs link to files that exist and that the commands they show are real. No Modal account is needed:

```bash
pip install -r sample_app/requirements.txt
cd sample_app && python -m pytest -q
```
