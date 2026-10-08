"""Issue agent: a GitHub issue labelled `agent` becomes a PR, with Claude Code working inside a Modal Sandbox.

Works on every repo the GitHub token (GH_DEMO_TOKEN) can push to:

    python agent/run.py --watch                   # watch all those repos for issues labelled `agent`
    python agent/run.py --issue owner/name#3      # handle one issue

The agent writes the change, tests for it (a recorded browser test for web apps) and a verify script. The
orchestrator runs that script in the sandbox; on failure the output goes back to the same agent session, up to
MAX_ROUNDS times. The passing run's recording becomes screenshots and a GIF in the PR.

This script is the orchestrator and holds the GitHub token: it clones the repo, uploads it to the sandbox and
pushes the resulting diff. The sandbox only ever sees the model credential.
"""

import argparse
import asyncio
import base64
import getpass
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import gh
import httpx
import modal

MODEL = os.environ.get("AGENT_MODEL", "haiku")
MODEL_AUTH = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
WORKDIR = "/repo"
VERIFY = "/tmp/agent/verify.sh"  # written by the agent, outside the repo so it isn't part of the PR
VERIFY_CMD = f"rm -rf /tmp/demo && mkdir -p /tmp/demo && DEMO_DIR=/tmp/demo timeout 900 sh {VERIFY}"
MAX_ROUNDS = 3  # verify runs; after a failure the agent gets the output and another go
DEMO_DIR = "/tmp/demo"
MEDIA_MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".gif": b"GIF8"}  # the only files accepted from the sandbox for the PR
MAX_MEDIA_BYTES = 5_000_000
GIT_IDENT = ["-c", "user.name=sandbox-agent", "-c", "user.email=sandbox-agent@users.noreply.github.com"]
EGRESS = [
    "api.anthropic.com",  # the model
    "pypi.org", "files.pythonhosted.org", "registry.npmjs.org",  # package installs
    "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",  # front-end assets, so demo pages render (e.g. FastAPI /docs)
]  # fmt: skip
TOKEN_RE = re.compile(r"sk-ant-oat\d+-[A-Za-z0-9_-]+")

app = modal.App.lookup("sandbox-demo", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl", "ffmpeg")
    .run_commands("curl -fsSL https://claude.ai/install.sh | bash")
    .pip_install("playwright")
    .run_commands("playwright install --with-deps chromium")  # for the agent's recorded browser tests
    .env(
        {
            "PATH": "/root/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "IS_SANDBOX": "1",  # lets Claude Code skip permission prompts as root: the sandbox is the boundary
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
        }
    )
)


def setup_token() -> str:
    """Run `claude setup-token` (interactive browser login) and capture the token it prints."""
    print("No valid Claude subscription token in .env: running `claude setup-token`, log in in the browser.")
    with tempfile.NamedTemporaryFile() as log:
        # `script` keeps a real TTY for the login UI while recording its output; wide columns stop the token wrapping.
        # ponytail: macOS/BSD `script` syntax; Linux needs `script -qc "<cmd>" <file>`
        subprocess.run(["script", "-q", log.name, "sh", "-c", "stty cols 1000; claude setup-token"], check=True)
        found = TOKEN_RE.findall(Path(log.name).read_text(errors="ignore"))
    return found[-1] if found else getpass.getpass("Couldn't read the token from the output; paste it: ").strip()


def model_auth() -> dict[str, str]:
    """Credentials for Claude Code: the shell environment wins; otherwise the subscription token cached in .env,
    refreshed via `claude setup-token` when missing or past the expiry recorded alongside it."""
    if auth := {k: os.environ[k] for k in MODEL_AUTH if os.environ.get(k)}:
        return auth
    env = gh.read_env()
    token, expires = env.get("CLAUDE_CODE_OAUTH_TOKEN"), env.get("CLAUDE_CODE_OAUTH_TOKEN_EXPIRES", "1970-01-01")
    if not token or date.fromisoformat(expires) <= date.today():
        token = setup_token()
        # ponytail: setup-token tokens last a year and are opaque, so expiry is tracked by date; a revoked token isn't detected
        expires = str(date.today() + timedelta(days=364))
        # Replace only the Claude lines, keeping whatever else you put in .env (GH_DEMO_TOKEN, comments, ...)
        kept = [line for line in gh.ENV_FILE.read_text().splitlines() if not line.startswith("CLAUDE_CODE_OAUTH_TOKEN")] if gh.ENV_FILE.exists() else []
        gh.ENV_FILE.write_text("\n".join([*kept, f"CLAUDE_CODE_OAUTH_TOKEN={token}", f"CLAUDE_CODE_OAUTH_TOKEN_EXPIRES={expires}"]) + "\n")
        gh.ENV_FILE.chmod(0o600)
        print(f"Saved token to {gh.ENV_FILE} (expires {expires})")
    return {"CLAUDE_CODE_OAUTH_TOKEN": token}


class AgentFailed(Exception):
    pass


async def sh(sb: modal.Sandbox, *cmd: str, workdir: str = WORKDIR) -> tuple[int, str]:
    p = await sb.exec.aio(*cmd, workdir=workdir)
    out = await p.stdout.read.aio()  # stdout only: stderr warnings would corrupt the git diff
    return await p.wait.aio(), out


def task_prompt(issue: dict) -> str:
    return f"""Resolve GitHub issue #{issue['number']} in this repository.

# {issue['title']}

{issue['body'] or ''}

1. Make the change. Install any dependencies you need.
2. Add tests for it next to the project's existing tests; they are part of the change. If the project is a web
   app, include an end-to-end browser test using Python Playwright (headless Chromium is installed) that starts
   the app, uses the new behaviour and checks it works. When the environment variable DEMO_DIR is set, that
   browser test must record a video into it (browser.new_context(record_video_dir=os.environ["DEMO_DIR"])) and
   save 1-3 PNG screenshots there that show the change; keep the recorded part under 10 seconds.
3. Write {VERIFY}: a shell script that, run from the repository root, installs what the tests need and runs
   the project's whole test suite including your new tests, exiting non-zero on any failure.
4. After you finish, `{VERIFY_CMD}` is run and you get the output back if it fails. Run it that way yourself
   until it passes, and read the screenshots to check they show the change.

Do not commit. Finish with a two-sentence summary of what you changed."""


def retry_prompt(code: int, out: str) -> str:
    return (
        f"`{VERIFY_CMD}` failed (exit {code}):\n```\n{out[-3000:]}\n```\n"
        "Fix the code or tests so it passes; don't weaken or skip the checks. "
        "Finish with a two-sentence summary of everything you changed."
    )


async def run_claude(sb: modal.Sandbox, prompt: str, secret: modal.Secret, log, resume: str | None = None) -> tuple[str, str]:
    """Run Claude Code in the sandbox, streaming its steps; `resume` continues an earlier session.
    Returns its final summary and the session id."""
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--dangerously-skip-permissions", "--output-format", "stream-json"]
    p = await sb.exec.aio(*cmd, "--verbose", *(["--resume", resume] if resume else []), workdir=WORKDIR, secrets=[secret])
    summary, session, buffer = "", resume, ""
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
                summary, session = event.get("result", ""), event.get("session_id", session)
                log(f"agent finished: {event.get('num_turns')} turns, ${event.get('total_cost_usd', 0):.3f}")
    if await p.wait.aio() != 0:
        raise AgentFailed(f"Claude Code exited with an error:\n```\n{(await p.stderr.read.aio())[-1500:]}\n```")
    return summary, session


def git(d: str, *args: str, stdin: bytes | None = None) -> str:
    """git with the orchestrator's GitHub token, passed as a header so it is never written to disk."""
    auth = base64.b64encode(f"x-access-token:{gh.TOKEN}".encode()).decode()
    env = {**os.environ, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraheader"}
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {auth}"
    return subprocess.run(["git", "-C", d, *args], env=env, check=True, capture_output=True, input=stdin).stdout.decode()


async def upload(sb: modal.Sandbox, d: str) -> None:
    """Copy the local clone (with .git, so the sandbox can diff) into the sandbox at WORKDIR."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(d, arcname=".")
    await sb.filesystem.write_bytes.aio(buf.getvalue(), "/tmp/repo.tgz")
    code, _ = await sh(sb, "sh", "-c", f"mkdir -p {WORKDIR} && tar xzf /tmp/repo.tgz --no-same-owner -C {WORKDIR}", workdir="/")
    if code:
        raise AgentFailed("Could not unpack the repo in the sandbox.")


async def collect_demo(sb: modal.Sandbox) -> list[tuple[str, bytes]]:
    """Turn the agent's videos into GIFs (GitHub plays those inline) and pull PNG/GIF files out of the sandbox.
    The sandbox is untrusted, so each file is checked by extension, size and magic bytes, and its name sanitised."""
    palette = "fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
    to_gif = f'for f in {DEMO_DIR}/*.webm; do [ -e "$f" ] && ffmpeg -loglevel error -y -i "$f" -vf "{palette}" "${{f%.webm}}.gif"; done'
    await sh(sb, "sh", "-c", to_gif, workdir="/")
    try:
        entries = await sb.filesystem.list_files.aio(DEMO_DIR)
    except Exception:  # the agent didn't create the folder
        return []
    media = []
    for f in sorted(entries, key=lambda f: f.name)[:6]:
        magic = MEDIA_MAGIC.get(Path(f.name).suffix.lower())
        if magic and f.is_file() and f.size <= MAX_MEDIA_BYTES:
            data = await sb.filesystem.read_bytes.aio(f.path)
            if data.startswith(magic):
                media.append((re.sub(r"[^A-Za-z0-9._-]", "_", f.name), data))
    return media


def push_media(repo: str, number: int, media: list[tuple[str, bytes]]) -> str:
    """Push the demo files to their own branch, so the PR shows them without them being part of its diff.
    Returns the markdown that embeds them."""
    branch = f"agent-media-issue-{number}"
    with tempfile.TemporaryDirectory() as d:
        git(d, "init", "-q")
        for name, data in media:
            Path(d, name).write_bytes(data)
        git(d, "add", "-A")
        git(d, *GIT_IDENT, "commit", "-q", "-m", f"Demo media for #{number}")
        git(d, "push", "--force", f"https://github.com/{repo}", f"HEAD:refs/heads/{branch}")
    images = "\n".join(f"![{name}](https://github.com/{repo}/blob/{branch}/{name}?raw=true)" for name, _ in media)
    return f"\n\n**Demo** (recorded by the passing test run)\n\n{images}"


def last_line(text: str) -> str:
    return (text.strip().splitlines() or [""])[-1]


async def handle(repo: str, number: int, secret: modal.Secret) -> None:
    def log(msg: str) -> None:
        print(f"\033[1;35m[{repo}#{number}]\033[0m {msg}", flush=True)

    sb = None
    with tempfile.TemporaryDirectory() as d:
        try:
            await gh.relabel(repo, number, "agent", "agent-working")
            issue = await gh.get_issue(repo, number)
            log(f"picked up: {issue['title']}")
            await gh.comment(repo, number, "Picked up by the agent. Working in a Modal Sandbox.")

            await asyncio.to_thread(git, d, "clone", "--depth", "1", f"https://github.com/{repo}", ".")
            sb = await modal.Sandbox.create.aio(
                app=app,
                image=image,
                timeout=3600,
                outbound_domain_allowlist=EGRESS,
                tags={"issue": str(number), "repo": repo},
            )
            log(f"sandbox {sb.object_id}")
            await upload(sb, d)
            summary, session = await run_claude(sb, task_prompt(issue), secret, log)
            # The agent's own "tests pass" isn't trusted: the orchestrator runs its verify script and loops on failure.
            for attempt in range(1, MAX_ROUNDS + 1):
                code, out = await sh(sb, "sh", "-c", f"{VERIFY_CMD} 2>&1")
                if code == 0:
                    break
                log(f"\033[33mverify failed (round {attempt}/{MAX_ROUNDS}):\033[0m {last_line(out)}")
                if attempt == MAX_ROUNDS:
                    raise AgentFailed(f"Still failing after {MAX_ROUNDS} rounds:\n```\n{out[-2000:]}\n```")
                summary, session = await run_claude(sb, retry_prompt(code, out), secret, log, resume=session)
            log(f"verify passed (round {attempt}): {last_line(out)}")
            _, script = await sh(sb, "cat", VERIFY)
            tests = (
                f"\n\n**Verified** in the sandbox, round {attempt} of {MAX_ROUNDS}: {last_line(out)}"
                f"\n\n<details><summary>verify script (written by the agent)</summary>\n\n```sh\n{script.strip()}\n```\n</details>"
            )
            await sh(sb, "git", "add", "-A")
            # never ship the agent's edits to CI config: workflows in the target repo run with its secrets
            _, diff = await sh(sb, "git", "diff", "--cached", "--binary", "--", ".", ":!.github")
            if not diff.strip():
                raise AgentFailed("The agent made no changes.")

            branch, title = f"agent/issue-{number}", f"Fix #{number}: {issue['title']}"
            await asyncio.to_thread(git, d, "checkout", "-b", branch)
            await asyncio.to_thread(git, d, "apply", "--binary", "-", stdin=diff.encode())
            await asyncio.to_thread(git, d, "add", "-A")
            # The sandbox is untrusted, so its pathspec filter above is a convenience; this host-side check is the guard.
            # -z: raw, unquoted paths (quoted ones would dodge the prefix check); --no-renames: list both ends of a rename
            out = await asyncio.to_thread(git, d, "diff", "--cached", "--name-only", "--no-renames", "-z")
            if blocked := [f for f in out.split("\0") if f.lower().startswith(".github/") or f.lower() == ".gitmodules"]:
                raise AgentFailed(f"Refusing to push changes to CI/submodule config: {', '.join(blocked)}")
            await asyncio.to_thread(git, d, *GIT_IDENT, "commit", "-m", title)
            await asyncio.to_thread(git, d, "push", "--force", "origin", branch)

            demo = ""
            try:  # the passing verify run's recording, if it made one (not every repo is a web app)
                if media := await collect_demo(sb):
                    demo = await asyncio.to_thread(push_media, repo, number, media)
                    log(f"demo: {', '.join(name for name, _ in media)}")
            except Exception as e:  # a missing demo shouldn't block the PR
                log(f"demo skipped: {e!r}")
            await sb.terminate.aio()
            pr = await gh.open_pr(repo, branch, title, f"Closes #{number}\n\n{summary}{tests}{demo}")
            await gh.comment(repo, number, f"Opened {pr}")
            await gh.relabel(repo, number, "agent-working", "agent-done")
            log(f"\033[1;32mPR {pr}\033[0m")
        except Exception as e:
            if sb:
                await sb.terminate.aio()
            if isinstance(e, subprocess.CalledProcessError):  # surface git's own error, minus any token
                e = AgentFailed(f"`git {e.cmd[3]}` failed:\n```\n{e.stderr.decode(errors='ignore')[-1500:]}\n```")
            reason = str(e) or repr(e)  # some exceptions (e.g. TimeoutError()) have an empty message
            log(f"\033[1;31mfailed: {reason.splitlines()[0]}\033[0m")
            await gh.comment(repo, number, f"The agent could not finish this issue.\n\n{reason}")
            await gh.relabel(repo, number, "agent-working", "agent-failed")


async def watch(secret: modal.Secret) -> None:
    print("Watching every repo this token can push to for issues labelled `agent` (Ctrl+C to stop)")
    seen, tasks, repos, refreshed = set(), set(), [], 0.0
    while True:
        try:
            if time.monotonic() - refreshed > 60:  # pick up new repos, and repos that just got their first issue
                repos, refreshed = await gh.watchable_repos(), time.monotonic()
                print(f"\033[2m  watching {len(repos)} repos\033[0m", flush=True)
            for repo in repos:
                for issue in await gh.labelled_issues(repo, "agent"):
                    if (repo, issue["number"]) not in seen:
                        seen.add((repo, issue["number"]))
                        task = asyncio.create_task(handle(repo, issue["number"], secret))
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)
        except httpx.HTTPError as e:  # a GitHub blip shouldn't stop the watcher
            print(f"\033[2m  GitHub poll failed, retrying: {e!r}\033[0m", flush=True)
        await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watch", action="store_true")
    group.add_argument("--issue", metavar="OWNER/NAME#N", help="handle one issue, e.g. mathaix/app#3")
    args = parser.parse_args()

    secret = modal.Secret.from_dict(model_auth())
    if args.issue:
        repo, _, number = args.issue.partition("#")
        if not number.isdigit():
            parser.error("--issue takes OWNER/NAME#N, e.g. mathaix/app#3")
        asyncio.run(handle(repo, int(number), secret))
    else:
        asyncio.run(watch(secret))
