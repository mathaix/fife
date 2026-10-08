# PRD: Modal Sandboxes talk demo

## Purpose

A public repo of live demos for a developer talk that answers three questions:
1. **What** are sandboxes? Disposable, isolated computers created, driven and destroyed from code.
2. **Why** are they useful? You can run untrusted code safely and get reproducible environments instantly.
3. **How** do they speed up development? An agent turns GitHub issues into tested PRs, working inside sandboxes.

**Audience:** developers. The code is the slide, so every file has to be short enough to read on screen.

## Goals

- Every demo runs live from a terminal with one command and finishes in under 2 minutes.
- Each demo shows a single idea, with timed, labelled output.
- The finale shows a realistic development workflow, not a toy, and anyone can reproduce it by forking the repo.

## Non-goals

- No web UI, no hosted service, and no support for multiple repos in the agent.
- No auto-merge: a human always reviews the agent's PRs.
- No custom LLM loop: the agent is an off-the-shelf CLI (Claude Code).

## Act 1: What (`demos/act1_hello.py`)

| ID | Requirement |
|---|---|
| A1.1 | Create a sandbox and print its id |
| A1.2 | Run a shell command and print the output |
| A1.3 | Stream a Python process's output line by line as it runs |
| A1.4 | Terminate the sandbox |

## Act 2: Why

| ID | Requirement |
|---|---|
| A2.1 | `act2_isolation.py`: an outbound HTTP call fails under `block_network=True` |
| A2.2 | `act2_isolation.py`: an infinite loop is killed by the sandbox `timeout` |
| A2.3 | `act2_isolation.py`: a memory hog is OOM-killed under a hard memory limit |
| A2.4 | `act2_snapshots.py`: sandbox A does a slow setup and is snapshotted; sandbox B boots from the snapshot with the setup already done; both timings are printed |

## Act 3: How (`agent/`, `sample_app/`)

**Flow:** a GitHub issue is labelled `agent` → the orchestrator → a Modal sandbox running Claude Code → the orchestrator verifies the work → a PR that closes the issue, plus a live preview.

| ID | Requirement |
|---|---|
| A3.1 | `sample_app/`: a small FastAPI app with a passing pytest suite and 3 seeded issues (a bug, a new endpoint, validation) |
| A3.2 | `agent/seed_issues.py` creates the labels and the 3 issues; `--reset` closes earlier agent PRs and issues and deletes their branches |
| A3.3 | `agent/run.py --watch` polls for open issues labelled `agent` and handles each one concurrently, one sandbox per issue |
| A3.4 | `agent/run.py --issue N` handles a single issue (rehearsal / retry) |
| A3.5 | Issue status shows in labels: `agent` → `agent-working` → `agent-done` / `agent-failed`, with a comment at pickup and at the end |
| A3.6 | The sandbox image has git, Claude Code and the app's dependencies baked in; outbound traffic is allowed only to `api.anthropic.com` and `github.com` |
| A3.7 | Claude Code runs headless (`claude -p`) with the issue as the prompt; its steps (tool calls, messages, final turns and cost) stream to the terminal, prefixed with the issue number |
| A3.8 | The orchestrator reruns `pytest` itself; if it fails, or the diff is empty, the issue is marked failed and the logs are posted |
| A3.9 | The orchestrator takes `git diff` out of the sandbox, then commits and pushes it from outside; **the GitHub token never enters the sandbox** |
| A3.10 | The orchestrator opens a PR with `Closes #N`, the agent's summary and the test result |
| A3.11 | The app is started inside the sandbox and its tunnel URL (`/docs`) is posted on the PR and the issue; the sandbox expires after at most 1 hour |

## Non-functional requirements

- **Security:** the sandbox holds only the model credential (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`), injected as a `modal.Secret` into the agent process alone. GitHub and Modal credentials stay with the orchestrator.
- **Cost:** defaults to the `sonnet` model on a Claude subscription token; `AGENT_MODEL` overrides it.
- **Reliability on stage:** the seeded issues are small and clearly specified. After one rehearsal, Modal has the images cached. A recorded fallback run exists.
- **Simplicity:** dependencies are only `modal` and `httpx`; there's no framework, and each file reads top to bottom.

## Credentials

| Name | Used by | Required for |
|---|---|---|
| `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | Orchestrator | All acts |
| `CLAUDE_CODE_OAUTH_TOKEN` (or `ANTHROPIC_API_KEY`) | Claude Code, inside the sandbox | Act 3 |
| `GH_DEMO_TOKEN` | Orchestrator | Act 3 |
| `GITHUB_REPOSITORY` | Orchestrator | Act 3 |

## Acceptance criteria

1. `./run_all.sh` completes Acts 1–2 against a real Modal account, and each step prints its timing.
2. Running `seed_issues.py --label` and then `run.py --watch` gives 3 issues handled in parallel and at least 2 PRs with passing tests and working preview URLs, in under 10 minutes.
3. In an issue that fails, the logs are posted and the issue is labelled `agent-failed`.
4. No GitHub or Modal credential appears in the sandbox's environment, files or logs.

## Open questions

- Talk length: does it fit all 3 acts or a trimmed set?
- Do we add the Codex CLI as a second agent (`--agent codex`) to show the sandbox doesn't care which agent runs?
