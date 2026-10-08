<p align="center">
  <img src="docs/logo.svg" alt="Modal Sandboxes logo: a terminal window inside a dashed sandbox boundary" width="640">
</p>

# Modal Sandboxes: what they are, why they're useful, and how they speed up development

Runnable demos for a developer talk on [Modal Sandboxes](https://modal.com/docs/guide/sandbox):
throwaway, locked-down cloud containers you create, drive and destroy from code.

The talk is in three acts. Acts 1 and 2 are one short file per idea; Act 3 is an agent that turns
GitHub issues into tested pull requests, with Claude Code working inside a sandbox.

## Setup

```bash
pip install -r requirements.txt
modal setup                     # or export MODAL_TOKEN_ID / MODAL_TOKEN_SECRET
```

For Act 3 also set:

| Variable | What |
|---|---|
| `GITHUB_REPOSITORY` | `owner/repo` of your fork of this repo (public, so the sandbox can clone it) |
| `GH_DEMO_TOKEN` | Fine-grained token for that repo: Contents, Issues, Pull requests (read/write). In GitHub Actions the built-in `GITHUB_TOKEN` is used instead |
| `CLAUDE_CODE_OAUTH_TOKEN` | From `claude setup-token`; runs on your Claude Pro/Max subscription. Or set `ANTHROPIC_API_KEY` instead |
| `AGENT_MODEL` | Optional, defaults to `haiku` |

## Repository layout

| Path | What's there |
|---|---|
| `demos/` | Acts 1 and 2: one short script per idea, run against Modal |
| `agent/` | Act 3: the issue agent (`run.py`), the GitHub client (`gh.py`) and the demo issue seeder (`seed_issues.py`) |
| `sample_app/` | The FastAPI bookshelf app the agent works on, with its pytest suite |
| `docs/` | Architecture walkthrough, diagrams and the interactive workflow page |
| `.github/workflows/agent.yml` | Optional GitHub Actions trigger for the issue agent |
| `run_all.sh` | Smoke-runs the Act 1 and Act 2 demos (needs Modal credentials) |
| `PRD.md` | Requirements the demos are built against |

## Running the tests

The sample app's tests cover the endpoints the agent changes. They also check that the README and
docs link to files that exist and that the commands they show are real. No Modal account is needed:

```bash
pip install -r sample_app/requirements.txt
cd sample_app && python -m pytest -q
```

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

Run `python agent/run.py --watch` on your laptop. Create an issue and label it `agent`;
Python polls for newly seen issues and dispatches one sandbox per issue while continuing to watch.
Claude Code works inside Modal, and your laptop verifies and publishes the results.
Keep the laptop awake and `AGENT_TRIGGER` unset so the optional Actions workflow does not start duplicate jobs.

Download [the interactive workflow diagram](docs/laptop-workflow.html) and open it locally to explore
each step, or use [the SVG](docs/laptop-workflow.svg) in slides. No hosted VM or Actions runner is required.

### Architecture

![Architecture: Python creates a Modal sandbox from an image with Claude Code installed, starts the coding agent, reruns tests, and publishes a PR.](docs/architecture.svg)

**Python orchestrates the job; Claude Code orchestrates the coding work inside the sandbox.**
The CLI is installed when Modal builds the reusable image, not on the orchestrator's machine.
The Claude model runs remotely on Anthropic's servers.

See [the architecture walkthrough and sequence diagram](docs/architecture.md) for the image build,
per-issue lifecycle, credential boundaries, and failure path.

```
GitHub issue labelled `agent`
   │  python agent/run.py --watch      (running on your laptop)
   ▼
Orchestrator (agent/run.py): holds the GitHub token
   1. relabel the issue, comment "picked up"
   2. create a sandbox: Claude Code + deps baked into the image,
      egress allowed only to api.anthropic.com and github.com
   3. clone the repo, run `claude -p "<issue>"` inside the sandbox, stream what it does
   4. run pytest itself; don't trust the agent's word
   5. pull out `git diff`, commit and push it from the orchestrator, open a PR that closes the issue
   6. start the app in the sandbox and post its tunnel URL as a live preview
```

- **Safety:** the agent runs arbitrary commands with permissions skipped, which is fine because the
  sandbox is the boundary. It only holds the model credential; the GitHub token never enters it.
- **Speed:** each issue gets a ready-to-go environment in seconds.
- **Scale:** label three issues and three sandboxes work in parallel.
- **Review:** the agent never merges. A human reviews the PR and clicks the preview.

The agent works on `sample_app/`, a small FastAPI app with tests. To run it:

```bash
python agent/seed_issues.py             # create the three demo issues (add --reset between rehearsals)
python agent/run.py --watch             # then label issues `agent` in the GitHub UI, live
```

**Optional Actions trigger:** `.github/workflows/agent.yml` runs the same script on `issues: labeled`, so
there's no server to run: GitHub is the trigger, Modal is the compute. Each labelled issue runs
`python agent/run.py --issue <number>` once, instead of the `--watch` loop. Enable it by setting the repo
variable `AGENT_TRIGGER=actions`, adding the Modal and Claude secrets to the repo, and allowing
"GitHub Actions to create and approve pull requests" in the repo's Actions settings.

## Tips for running live

- Do a full rehearsal first. Modal caches the images, so nothing builds on stage.
- Keep each file open next to the terminal; the code is the slide.
- Watch sandboxes appear in the Modal dashboard while the agent runs.
- Record a fallback run in case the venue Wi-Fi or the model misbehaves.
- On a subscription token, parallel agents share your plan's usage limits.
