# Architecture: GitHub issue to pull request

**The Python program manages jobs. Claude Code manages the coding loop inside each job's sandbox.**

## Laptop polling and dispatch workflow

The talk demo runs the orchestrator on your laptop with `python agent/run.py --watch`.
You create a GitHub issue and label it `agent`; Python polls every five seconds and dispatches
a fresh Modal sandbox for each newly seen issue. It continues polling while jobs run concurrently.
After Claude Code finishes, Python requests tests and retrieves the patch, then publishes the
branch, PR and preview link from your laptop.

![Laptop issue-to-PR workflow](laptop-workflow.svg)

Download [the interactive workflow diagram](laptop-workflow.html) and open it locally,
or use [the slide-ready SVG](laptop-workflow.svg).

## Component architecture

![Architecture](architecture.svg)

## Build once, reuse per issue

`agent/run.py` defines a Modal image with Python, Git, curl and the Claude Code CLI;
the agent installs the target repo's dependencies itself. Modal builds and caches that image. No credentials
are baked into it. Each issue gets a fresh sandbox created from the image.

The target repository is **cloned per issue** by the orchestrator, with its GitHub token, and
uploaded into the sandbox; it is not baked into this image, and private repos work. The separate
Act 2 snapshot demo illustrates filesystem snapshots, but the issue agent does not
currently boot from a repository snapshot.

## Per-issue sequence

```mermaid
sequenceDiagram
    actor Developer
    participant GitHub
    participant Python as Python orchestrator (laptop)
    participant Modal
    participant Sandbox as Sandbox with Claude Code installed
    participant Claude as Claude model (Anthropic)

    Note over Python,Modal: Image definition installs CLI and dependencies, and Modal caches the build
    Developer->>GitHub: Label an issue agent
    GitHub-->>Python: Polling result
    Python->>GitHub: Read issue, mark working, comment
    Python->>Modal: Sandbox.create(image, timeout, egress allowlist)
    Modal-->>Python: Sandbox handle
    Python->>Sandbox: Upload local clone (orchestrator cloned it with its token)
    Python->>Sandbox: claude -p with issue prompt and process-scoped model credential
    loop Claude Code's coding loop
        Sandbox->>Claude: Model request, context and tool results
        Claude-->>Sandbox: Next action
        Note over Sandbox: CLI reads files, edits code, runs tests
        Sandbox-->>Python: Stream agent events
    end
    Sandbox-->>Python: Agent exits
    Python->>Sandbox: Rerun AGENT_TEST_CMD (if set), collect git diff
    Sandbox-->>Python: Exit code, test output and patch
    alt Tests pass and patch is nonempty
        Python->>GitHub: Commit and push patch from outside sandbox
        Python->>Sandbox: Start app on port 8000
        Python->>Modal: Get HTTPS tunnel URL
        Python->>GitHub: Open PR, post preview, mark issue done
        Developer->>GitHub: Review PR (no automatic merge)
        Note over Modal,Sandbox: Preview remains until sandbox's 1-hour lifetime expires
    else Agent errors, tests fail or patch is empty
        Python->>GitHub: Post failure and mark issue failed
        Python->>Modal: Terminate sandbox
    end
```

## Responsibilities and credentials

| Component | Runs where | Responsibility | Credentials |
|---|---|---|---|
| Python orchestrator | Your laptop | Claim issue, create sandbox, start agent, request test rerun, extract patch, publish PR and update issue | GitHub and Modal credentials; supplies model credential to agent process |
| Claude Code CLI | Inside the Modal sandbox | Read and edit repository files, run commands, iterate with the model | `CLAUDE_CODE_OAUTH_TOKEN` (subscription), or `ANTHROPIC_API_KEY` |
| Claude model | Anthropic's servers | Reason over context and choose the CLI's next action | Receives authenticated model requests |
| Modal | Modal infrastructure | Build/cache image, provide isolation, execute commands, enforce lifetime and expose preview tunnel | Orchestrator authenticates with Modal token |

The sandbox does not receive the GitHub or Modal token. The model credential is
injected via `modal.Secret` into the Claude Code process; its subprocesses can inherit
it. Process-scoped injection is **not** a guarantee that agent-controlled code cannot
read or persist that credential.

The scaffold allows outbound traffic to `api.anthropic.com` for model calls and to the
PyPI and npm registries for dependency installs; the sandbox never talks to GitHub. Subscription authentication and any additional
required endpoints must be checked during rehearsal. The model is remote; it is
not installed or served inside the sandbox.

## Parallel work, previews and limits

- The local watcher starts concurrent issue jobs, each with its own sandbox.
- Successful sandboxes stay alive for the preview, subject to the 1-hour total lifetime
  measured from creation, not an additional hour after completion.
- Failed jobs attempt to terminate their sandbox immediately.
- A human reviews every PR. The orchestrator does not merge.

## Current verification status

This documents the initial scaffold, not a production-hardened service. The full
Modal/GitHub/subscription flow has not been run end to end.

The test rerun runs the agent's edited tests in its own workspace, so it does not
prove the change meets the issue's requirements. Trusted acceptance tests, restricted
patch paths, bounded concurrency, durable job claims/retries, and stricter credential
handling are follow-ups before using this against untrusted issues or real repositories.
