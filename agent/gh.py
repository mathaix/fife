"""Minimal GitHub REST client for the issue agent (repo from GITHUB_REPOSITORY, token from GH_DEMO_TOKEN or GITHUB_TOKEN)."""

import os

import httpx

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ.get("GH_DEMO_TOKEN") or os.environ["GITHUB_TOKEN"]

_client = httpx.AsyncClient(
    base_url=f"https://api.github.com/repos/{REPO}",
    headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    timeout=30,
)


async def _call(method: str, path: str, **kwargs):
    r = await _client.request(method, path, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else None


async def get_issue(number: int) -> dict:
    return await _call("GET", f"/issues/{number}")


async def labelled_issues(label: str) -> list[dict]:
    issues = await _call("GET", "/issues", params={"labels": label, "state": "open"})
    return [i for i in issues if "pull_request" not in i]


async def create_issue(title: str, body: str, labels: list[str]) -> dict:
    return await _call("POST", "/issues", json={"title": title, "body": body, "labels": labels})


async def close_issue(number: int) -> None:
    await _call("PATCH", f"/issues/{number}", json={"state": "closed"})


async def comment(number: int, body: str) -> None:
    await _call("POST", f"/issues/{number}/comments", json={"body": body})


async def relabel(number: int, old: str, new: str) -> None:
    try:
        await _call("DELETE", f"/issues/{number}/labels/{old}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
    await _call("POST", f"/issues/{number}/labels", json={"labels": [new]})


async def ensure_label(name: str, color: str) -> None:
    try:
        await _call("POST", "/labels", json={"name": name, "color": color})
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 422:  # already exists
            raise


async def open_pr(head: str, title: str, body: str) -> str:
    base = (await _call("GET", ""))["default_branch"]
    return (await _call("POST", "/pulls", json={"head": head, "base": base, "title": title, "body": body}))["html_url"]


async def open_agent_prs() -> list[dict]:
    return [p for p in await _call("GET", "/pulls", params={"state": "open"}) if p["head"]["ref"].startswith("agent/")]


async def close_pr_and_branch(pr: dict) -> None:
    await _call("PATCH", f"/pulls/{pr['number']}", json={"state": "closed"})
    await _call("DELETE", f"/git/refs/heads/{pr['head']['ref']}")
