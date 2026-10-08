"""Minimal GitHub REST client for the issue agent. Token from GH_DEMO_TOKEN; repos are whatever it can access.

Importing this also loads settings from .env at the harness root (variables already set in the shell win).
"""

import os
import sys
from pathlib import Path

import httpx

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def read_env() -> dict[str, str]:
    """KEY=value lines from .env; full-line # comments are skipped (no inline comments), surrounding quotes stripped."""
    if not ENV_FILE.exists():
        return {}
    lines = [line for line in ENV_FILE.read_text().splitlines() if "=" in line and not line.lstrip().startswith("#")]
    return {k.strip(): v.strip().strip("\"'") for k, v in (line.split("=", 1) for line in lines)}


for key, value in read_env().items():
    if not key.startswith("CLAUDE_CODE_OAUTH_TOKEN"):  # run.py owns the Claude token, since it also checks its expiry
        os.environ.setdefault(key, value)

TOKEN = os.environ.get("GH_DEMO_TOKEN") or sys.exit(f"Set GH_DEMO_TOKEN in {ENV_FILE} or in your shell (see README).")
LABELS = {"agent": "5319e7", "agent-working": "fbca04", "agent-done": "0e8a16", "agent-failed": "d93f0b"}

_client = httpx.AsyncClient(
    base_url="https://api.github.com",
    headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    timeout=30,
)


async def _call(method: str, path: str, **kwargs):
    r = await _client.request(method, path, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else None


async def get_issue(repo: str, number: int) -> dict:
    return await _call("GET", f"/repos/{repo}/issues/{number}")


async def watchable_repos() -> list[str]:
    """Repos the token can push to, not archived, with issues enabled and at least one open issue."""
    repos, page = [], 1
    while batch := await _call("GET", "/user/repos", params={"per_page": 100, "page": page}):
        repos += [
            r["full_name"] for r in batch
            if r["permissions"]["push"] and not r["archived"] and r["has_issues"] and r["open_issues_count"]
        ]  # fmt: skip
        page += 1
    return repos


_etags: dict[tuple[str, str], tuple[str, list[dict]]] = {}


async def labelled_issues(repo: str, label: str) -> list[dict]:
    # Conditional request: an unchanged list comes back as 304, which doesn't count against the rate limit.
    etag, cached = _etags.get((repo, label), ("", []))
    r = await _client.get(f"/repos/{repo}/issues", params={"labels": label, "state": "open"}, headers={"If-None-Match": etag})
    if r.status_code == 304:
        return cached
    r.raise_for_status()
    issues = [i for i in r.json() if "pull_request" not in i]
    _etags[(repo, label)] = (r.headers.get("ETag", ""), issues)
    return issues


async def create_issue(repo: str, title: str, body: str, labels: list[str]) -> dict:
    return await _call("POST", f"/repos/{repo}/issues", json={"title": title, "body": body, "labels": labels})


async def close_issue(repo: str, number: int) -> None:
    await _call("PATCH", f"/repos/{repo}/issues/{number}", json={"state": "closed"})


async def comment(repo: str, number: int, body: str) -> None:
    await _call("POST", f"/repos/{repo}/issues/{number}/comments", json={"body": body})


async def relabel(repo: str, number: int, old: str, new: str) -> None:
    try:
        await _call("DELETE", f"/repos/{repo}/issues/{number}/labels/{old}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
    await _call("POST", f"/repos/{repo}/issues/{number}/labels", json={"labels": [new]})


async def ensure_labels(repo: str) -> None:
    for name, color in LABELS.items():
        try:
            await _call("POST", f"/repos/{repo}/labels", json={"name": name, "color": color})
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 422:  # already exists
                raise


async def open_pr(repo: str, head: str, title: str, body: str) -> str:
    base = (await _call("GET", f"/repos/{repo}"))["default_branch"]
    return (await _call("POST", f"/repos/{repo}/pulls", json={"head": head, "base": base, "title": title, "body": body}))["html_url"]


async def open_agent_prs(repo: str) -> list[dict]:
    return [p for p in await _call("GET", f"/repos/{repo}/pulls", params={"state": "open"}) if p["head"]["ref"].startswith("agent/")]


async def delete_media_branches(repo: str) -> None:
    for ref in await _call("GET", f"/repos/{repo}/git/matching-refs/heads/agent-media-"):
        await _call("DELETE", f"/repos/{repo}/git/{ref['ref']}")


async def close_pr_and_branch(repo: str, pr: dict) -> None:
    await _call("PATCH", f"/repos/{repo}/pulls/{pr['number']}", json={"state": "closed"})
    await _call("DELETE", f"/repos/{repo}/git/refs/heads/{pr['head']['ref']}")
