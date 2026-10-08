# Modal Sandboxes: what they are, why they're useful, and how they speed up development

Runnable demos for a developer talk on [Modal Sandboxes](https://modal.com/docs/guide/sandbox):
throwaway, locked-down cloud containers you create, drive and destroy from code.

The talk is in three acts. Acts 1 and 2 are one short file per idea; Act 3 is an agent that turns
GitHub issues into tested pull requests, with Claude Code working inside a sandbox.

## Setup

```bash
make setup                      # creates .venv (needs uv); `make` lists all commands
modal setup                     # or export MODAL_TOKEN_ID / MODAL_TOKEN_SECRET
```

For Act 3, put these in a `.env` file in this folder (gitignored), one `KEY=value` per line, or export
them in your shell (the shell wins). Full-line `#` comments are fine; inline comments are not.

```
GH_DEMO_TOKEN=github_pat_...
```

| Variable | What |
|---|---|
| `GH_DEMO_TOKEN` | Fine-grained GitHub token. The agent watches every repo this token can push to, so its repository access *is* the agent's scope. Permissions: Contents, Issues, Pull requests (read/write); leave Workflows off |
| `CLAUDE_CODE_OAUTH_TOKEN` | From `claude setup-token`; runs on your Claude Pro/Max subscription. Or set `ANTHROPIC_API_KEY` instead. If neither is set, `run.py` runs `claude setup-token` for you and caches the token in `.env` (gitignored) until it expires |
| `AGENT_MODEL` | Optional, defaults to `haiku` |

## Act 1: What is a sandbox?

`python demos/act1_hello.py` creates a sandbox, runs a shell command, streams Python output live and
terminates it. A fresh, isolated computer is one `Sandbox.create` away, and it's gone when you're done.

How it's orchestrated: **your code is the orchestrator, the sandbox is a passive worker.**

```
your code ──Modal SDK──► Modal ──► sandbox 1 … sandbox N
   create → exec / upload → read stdout, files → decide next step → terminate
```

## Act 2: Why is that useful?

| Demo | Shows | Takeaway |
|---|---|---|
| `python demos/act2_isolation.py` | A network call fails with `block_network=True`; an infinite loop is killed at `timeout=10`; a memory hog is OOM-killed at its limit | Untrusted code (from an LLM, a contributor, a dependency) can't phone home, run forever or take the host down |
| `python demos/act2_snapshots.py` | Slow setup in sandbox A, `snapshot_filesystem()`, sandbox B boots from it with everything installed | Set up an environment once, clone it instantly: no "works on my machine" |

## Act 3: How does it speed up development? An issue-to-PR agent

### Laptop workflow (the talk demo)

![Laptop workflow: create an issue and label it agent; Python polls GitHub every five seconds, dispatches a Modal sandbox, verifies the result and publishes a PR with a preview.](docs/laptop-workflow.svg)

Run `python agent/run.py --watch` on your laptop, then label an issue `agent` in any repo your token can
push to. Claude Code works inside a Modal sandbox; your laptop verifies and publishes the result.

Download [the interactive workflow diagram](docs/laptop-workflow.html) and open it locally to explore
each step, or use [the SVG](docs/laptop-workflow.svg) in slides.

### Architecture

![Architecture: Python creates a Modal sandbox from an image with Claude Code installed, starts the coding agent, reruns tests, and publishes a PR.](docs/architecture.svg)

**Python orchestrates the job; Claude Code orchestrates the coding work inside the sandbox.**
The CLI is installed when Modal builds the reusable image, not on the orchestrator's machine.
The Claude model runs remotely on Anthropic's servers.

See [the architecture walkthrough and sequence diagram](docs/architecture.md) for the image build,
per-issue lifecycle, credential boundaries, and failure path.

### The workflow, step by step

There are three parts: **your laptop** runs `agent/run.py` and holds the GitHub token; **Modal** gives each
issue a fresh, throwaway sandbox where Claude Code runs; **Claude** (the model) runs on Anthropic's servers.

1. **Start up.** `python agent/run.py --watch`. If no Claude credential is set and `.env` has no valid
   subscription token, it runs `claude setup-token` (you log in in the browser) and saves the token to `.env`.
2. **Watch.** Every minute it asks GitHub which repos the token can push to (skipping archived repos and
   repos with no open issues). Every 5 seconds it checks those repos for open issues labelled `agent`.
3. **Pick up.** For each new labelled issue: relabel it `agent-working`, comment "Picked up", and clone the
   issue's repo on the laptop with the token. Several issues run at once, each independently.
4. **Sandbox.** Create a Modal sandbox and upload the clone into it. The sandbox gets the Claude credential
   only, never the GitHub token, and can reach only `api.anthropic.com`, the PyPI/npm registries and the
   jsDelivr/unpkg/cdnjs CDNs (so web pages render in browser tests).
5. **Agent.** Claude Code gets the issue text and is told to: make the change; add tests next to the existing
   ones (for a web app, an end-to-end Playwright browser test that records a video and screenshots when
   `DEMO_DIR` is set); and write `/tmp/agent/verify.sh`, a script that runs the whole test suite. It doesn't
   commit. Its steps stream to your terminal.
6. **Verify, in the same sandbox.** The orchestrator runs `verify.sh` itself rather than trusting the agent's
   word. If it fails, the output goes back to the same Claude session ("this failed, fix it"), and the check
   runs again, up to 3 rounds; after that the issue is marked failed with the last output.
7. **Check the change, on the laptop.** Pull the diff out, apply it to the laptop's clone, and refuse to
   continue if it touches `.github/` (workflows run with the repo's secrets).
8. **Publish.** Commit to branch `agent/issue-N` and push. If the passing run recorded anything, turn the
   video into a GIF (GitHub plays those inline), take only genuine PNG/GIF files under 5 MB, and push them to
   a separate branch `agent-media-issue-N`, so they show in the PR without being part of its changes. Shut
   the sandbox down, open a PR that says "Closes #N" with the agent's summary, the verify result and script,
   and the demo images; comment the link on the issue and relabel it `agent-done`.
9. **On failure** at any step: shut the sandbox down, comment the reason on the issue, relabel it
   `agent-failed`.

**Your part:** label an issue `agent` (create the label in the repo the first time), wait, review the PR
(with the recording from the passing test run, when the repo is a web app).
The agent never merges.

- **Safety:** the agent runs arbitrary commands with permissions skipped, which is fine because the
  sandbox is the boundary. It only holds the model credential; the GitHub token never enters it.
- **Speed:** each issue gets a ready-to-go environment in seconds.
- **Scale:** label three issues and three sandboxes work in parallel.

### Running it

```bash
make watch                      # every repo the token can push to
make issue ISSUE=owner/name#3   # one issue, e.g. to retry a failed one
make seed REPO=owner/name       # the three sample_app demo issues
make demos                      # Acts 1 and 2
```

A failed issue isn't retried while `--watch` keeps running; restart it, or use `--issue`. Per-repo guidance
for the agent (how to run the tests, code style) goes in a `CLAUDE.md` at the target repo's root, which Claude
Code reads automatically.

For the talk, `sample_app/` (a small FastAPI app with three seeded bugs) is a ready-made target. Copy it into
a repo of its own, then:

```bash
python agent/seed_issues.py --repo owner/name    # create the three demo issues (add --reset between rehearsals)
python agent/run.py --watch                      # then label issues `agent` in the GitHub UI, live
```

## Tips for running live

- Do a full rehearsal first. Modal caches the images, so nothing builds on stage.
- Keep each file open next to the terminal; the code is the slide.
- Watch sandboxes appear in the Modal dashboard while the agent runs.
- Record a fallback run in case the venue Wi-Fi or the model misbehaves.
- On a subscription token, parallel agents share your plan's usage limits.
