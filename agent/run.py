"""Issue agent: a GitHub issue labelled `agent` becomes a tested PR, with Claude Code working inside a Modal Sandbox.

    python agent/run.py --watch      # poll for labelled issues (on stage)
    python agent/run.py --issue 3    # handle one issue (GitHub Action)

This script is the orchestrator and holds the GitHub token. The sandbox only ever sees the model credential.
"""

import argparse
import asyncio
import base64
import json
import os
import subprocess
import tempfile

import gh
import modal
from modal.stream_type import StreamType

MODEL = os.environ.get("AGENT_MODEL", "haiku")
MODEL_AUTH = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
APP_DIR = "/repo/sample_app"

app = modal.App.lookup("sandbox-demo", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl")
    .run_commands("curl -fsSL https://claude.ai/install.sh | bash")
    .pip_install("fastapi", "uvicorn", "httpx", "pytest")
    .env(
        {
            "PATH": "/root/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "IS_SANDBOX": "1",  # lets Claude Code skip permission prompts as root: the sandbox is the boundary
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
        }
    )
)


class AgentFailed(Exception):
    pass


async def sh(sb: modal.Sandbox, *cmd: str, workdir: str = APP_DIR) -> tuple[int, str]:
    p = await sb.exec.aio(*cmd, workdir=workdir)
    out = await p.stdout.read.aio() + await p.stderr.read.aio()
    return await p.wait.aio(), out


async def run_claude(sb: modal.Sandbox, issue: dict, secret: modal.Secret, log) -> str:
    prompt = (
        f"Resolve GitHub issue #{issue['number']} in this FastAPI app.\n\n# {issue['title']}\n\n{issue['body']}\n\n"
        "Add or update tests in tests/ for the change. Run `python -m pytest -q` and make sure everything passes. "
        "Do not commit. Finish with a two-sentence summary of what you changed."
    )
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--dangerously-skip-permissions", "--output-format", "stream-json"]
    p = await sb.exec.aio(*cmd, "--verbose", workdir=APP_DIR, secrets=[secret])
    summary, buffer = "", ""
    async for chunk in p.stdout:
        buffer += chunk
        *lines, buffer = buffer.split("\n")
        for line in filter(None, lines):
            event = json.loads(line)
            if event["type"] == "assistant":
                for block in event["message"]["content"]:
                    if block["type"] == "text" and block["text"].strip():
                        log(block["text"].strip().splitlines()[0][:110])
                    elif block["type"] == "tool_use":
                        args = block["input"].get("command") or block["input"].get("file_path") or ""
                        log(f"\033[33m{block['name']}\033[0m {args[:100]}")
            elif event["type"] == "result":
                summary = event.get("result", "")
                log(f"agent finished: {event.get('num_turns')} turns, ${event.get('total_cost_usd', 0):.3f}")
    if await p.wait.aio() != 0:
        raise AgentFailed(f"Claude Code exited with an error:\n```\n{(await p.stderr.read.aio())[-1500:]}\n```")
    return summary


def push_branch(branch: str, diff: str, message: str) -> None:
    """Commit the sandbox's diff from the orchestrator, so the GitHub token never enters the sandbox."""
    auth = base64.b64encode(f"x-access-token:{gh.TOKEN}".encode()).decode()
    env = {**os.environ, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraheader"}
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {auth}"
    with tempfile.TemporaryDirectory() as d:

        def git(*args: str, stdin: str | None = None) -> None:
            subprocess.run(["git", "-C", d, *args], env=env, check=True, capture_output=True, input=stdin, text=True)

        git("clone", "--depth", "1", f"https://github.com/{gh.REPO}", ".")
        git("checkout", "-b", branch)
        git("apply", "-", stdin=diff)
        git("add", "-A")
        git("-c", "user.name=sandbox-agent", "-c", "user.email=sandbox-agent@users.noreply.github.com", "commit", "-m", message)
        git("push", "--force", "origin", branch)


async def handle(number: int, secret: modal.Secret) -> None:
    def log(msg: str) -> None:
        print(f"\033[1;35m[#{number}]\033[0m {msg}", flush=True)

    await gh.relabel(number, "agent", "agent-working")
    issue = await gh.get_issue(number)
    log(f"picked up: {issue['title']}")
    await gh.comment(number, "Picked up by the agent. Working in a Modal Sandbox.")

    sb = await modal.Sandbox.create.aio(
        app=app,
        image=image,
        timeout=3600,
        encrypted_ports=[8000],
        outbound_domain_allowlist=["api.anthropic.com", "github.com"],
        tags={"issue": str(number)},
    )
    try:
        log(f"sandbox {sb.object_id}")
        await sh(sb, "git", "clone", "--depth", "1", f"https://github.com/{gh.REPO}", "/repo", workdir="/")
        summary = await run_claude(sb, issue, secret, log)

        code, tests = await sh(sb, "python", "-m", "pytest", "-q")
        if code != 0:
            raise AgentFailed(f"Tests fail after the agent's changes:\n```\n{tests[-2000:]}\n```")
        log(f"tests pass: {tests.strip().splitlines()[-1]}")
        await sh(sb, "git", "add", "-A", workdir="/repo")
        _, diff = await sh(sb, "git", "diff", "--cached", workdir="/repo")
        if not diff.strip():
            raise AgentFailed("The agent made no changes.")

        branch = f"agent/issue-{number}"
        await asyncio.to_thread(push_branch, branch, diff, f"Fix #{number}: {issue['title']}")
        await sb.exec.aio(
            "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
            workdir=APP_DIR, stdout=StreamType.DEVNULL, stderr=StreamType.DEVNULL,
        )  # fmt: skip
        preview = (await sb.tunnels.aio())[8000].url + "/docs"
        body = f"Closes #{number}\n\n{summary}\n\n**Tests:** {tests.strip().splitlines()[-1]}\n\n**Preview:** {preview}"
        pr = await gh.open_pr(branch, f"Fix #{number}: {issue['title']}", body)
        await gh.comment(number, f"Opened {pr}\n\nLive preview (up to 1 hour): {preview}")
        await gh.relabel(number, "agent-working", "agent-done")
        log(f"\033[1;32mPR {pr}\033[0m")
        log(f"preview {preview}")
    except Exception as e:
        log(f"\033[1;31mfailed: {str(e).splitlines()[0]}\033[0m")
        await gh.comment(number, f"The agent could not finish this issue.\n\n{e}")
        await gh.relabel(number, "agent-working", "agent-failed")
        await sb.terminate.aio()


async def watch(secret: modal.Secret) -> None:
    print(f"Watching {gh.REPO} for issues labelled `agent` (Ctrl+C to stop)")
    seen, tasks = set(), set()
    while True:
        for issue in await gh.labelled_issues("agent"):
            if issue["number"] not in seen:
                seen.add(issue["number"])
                task = asyncio.create_task(handle(issue["number"], secret))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watch", action="store_true")
    group.add_argument("--issue", type=int)
    args = parser.parse_args()

    auth = {k: os.environ[k] for k in MODEL_AUTH if os.environ.get(k)}
    if not auth:
        raise SystemExit(f"Set one of {', '.join(MODEL_AUTH)} for Claude Code.")
    secret = modal.Secret.from_dict(auth)
    asyncio.run(handle(args.issue, secret) if args.issue else watch(secret))
