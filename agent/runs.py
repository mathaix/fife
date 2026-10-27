"""Pure logic of the issue agent (no GitHub, Modal or network): run records, `/agent` comment parsing,
session keys, the resume-fallback prompt and the dispatcher that decides what runs when. Kept apart from
run.py so it can be tested without credentials.
"""

import asyncio
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field

RECORD_MARKER = "<!-- agent-run-record -->"
AGENT_COMMAND = re.compile(r"\A\s*/agent(?:\s+(.*))?\Z", re.S)
BRANCH = re.compile(r"\Aagent/issue-(\d+)\Z")
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}  # author_association values allowed to spend the Claude subscription
MAX_SESSION_BYTES = 30_000_000  # a larger session file is not restored: resume falls back to a fresh session
MAX_COMMENT_DIFF = 30_000  # GitHub comments top out at 65536 characters; the full diff stays in the Volume
STAGES = ("clone", "agent", "verify", "push", "PR")


def parse_agent_comment(body: str | None) -> str | None:
    """The instructions of a `/agent <instructions>` comment, or None for any other comment.
    `/agentic` or `please /agent` do not count: only the command at the very start does."""
    m = AGENT_COMMAND.match(body or "")
    return (m.group(1) or "").strip() if m else None


def may_trigger(comment: dict) -> bool:
    return comment.get("author_association") in TRUSTED and not (comment.get("user") or {}).get("type") == "Bot"


def issue_number_from_branch(ref: str) -> int | None:
    m = BRANCH.match(ref)
    return int(m.group(1)) if m else None


def session_key(repo: str, number: int, session_id: str) -> str:
    return f"{repo}/issue-{number}/{session_id}.jsonl"


def meta_key(repo: str, number: int) -> str:
    return f"{repo}/issue-{number}/latest.json"


def diff_key(repo: str, number: int) -> str:
    return f"{repo}/issue-{number}/pending.diff"


def new_agent_comments(comments: list[dict], last_seen: dict[tuple[str, int], int], repo: str) -> list[dict]:
    """Comments (oldest first) that start a run: `/agent`, from a trusted author, newer than the last one seen
    on that issue. Updates `last_seen` for every comment, so ordinary ones are skipped but not revisited."""
    found = []
    for c in sorted(comments, key=lambda c: c["id"]):
        number = int(c["issue_url"].rsplit("/", 1)[1])
        if c["id"] <= last_seen.get((repo, number), 0):
            continue
        last_seen[(repo, number)] = c["id"]
        instructions = parse_agent_comment(c.get("body"))
        if instructions is not None and may_trigger(c):
            found.append({"number": number, "instructions": instructions, "id": c["id"]})
    return found


@dataclass
class Record:
    """What one run did; rendered as the single run-record comment on the issue."""

    status: str = "running"  # running | done | failed
    trigger: str = "label `agent`"
    stage: str = "clone"
    reason: str = ""
    rounds: int = 0
    cost: float = 0.0
    sandbox: str = ""
    session: str = ""  # Volume key of the saved session
    pr: str = ""
    resumed: str = ""  # how the Claude session was started: resumed / fresh / fallback
    diff_note: str = ""
    extra: list[str] = field(default_factory=list)


def render_record(r: Record, volume: str) -> str:
    rows = [
        ("Status", {"running": "working", "done": "done", "failed": "failed"}[r.status]),
        ("Trigger", r.trigger),
        ("Stage", f"{r.stage}" + (" (failed here)" if r.status == "failed" else "")),
        ("Verify rounds", str(r.rounds)),
        ("Cost", f"${r.cost:.3f}"),
        ("Sandbox", f"`{r.sandbox}`" if r.sandbox else "-"),
    ]
    if r.pr:
        rows.append(("PR", r.pr))
    if r.resumed:
        rows.append(("Claude session", r.resumed))
    if r.session:
        rows.append(("Saved session", f"`{r.session}` in Modal Volume `{volume}` (kept off GitHub: `modal volume get {volume} {r.session}`)"))
    text = f"{RECORD_MARKER}\n**Agent run record**\n\n| | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)
    if r.reason:
        text += f"\n\n{r.reason}"
    if r.diff_note:
        text += f"\n\n{r.diff_note}"
    if r.status == "failed":
        text += "\n\nRe-add the `agent` label to retry, or comment `/agent <instructions>` to steer the agent."
    elif r.status == "done":
        text += "\n\nComment `/agent <instructions>` on the issue or PR to ask for changes."
    return text


def diff_comment(diff: str, why: str) -> str:
    shown = diff if len(diff) <= MAX_COMMENT_DIFF else diff[:MAX_COMMENT_DIFF] + "\n... (truncated; the full diff is saved with the run)"
    return f"**Diff kept** ({why}). Comment `/agent` to apply it on a new branch and continue.\n\n<details><summary>diff</summary>\n\n```diff\n{shown}\n```\n</details>"


def fallback_prompt(issue: dict, pr_body: str, diff: str, instructions: str) -> str:
    """Fresh-session prompt used when the earlier Claude session cannot be resumed."""
    return f"""You are continuing earlier work on GitHub issue #{issue['number']} in this repository. The earlier
conversation is not available, so here is what is known.

# Issue: {issue['title']}

{issue.get('body') or ''}

# Pull request description (summary and verify result of the earlier run)

{pr_body or '(no pull request was opened)'}

# Changes made so far (the working tree already contains them)

```diff
{diff[-20000:] or '(none)'}
```

# New instructions

{instructions}

Make the requested changes, keep the tests and the verify script passing, and do not commit. Finish with an updated ledger."""


def dumps_meta(session: str, stage: str, reason: str, has_diff: bool, pr: str) -> bytes:
    return json.dumps({"session": session, "stage": stage, "reason": reason[:2000], "has_diff": has_diff, "pr": pr}).encode()


class Dispatcher:
    """Decides what runs. `run(repo, number, instructions)` does one run (instructions None = a labelled issue).

    - runs on one issue are serialised in arrival order, so two `/agent` comments never share a branch
    - `seen` stops a labelled issue starting twice while its run is being set up, and is cleared when the run
      ends, so re-adding `agent` after `agent-failed` retries without restarting the watcher
    """

    def __init__(self, run):
        self.run = run
        self.seen: set[tuple[str, int]] = set()
        self.last_comment: dict[tuple[str, int], int] = {}
        self.tasks: set[asyncio.Task] = set()
        self._locks: dict[tuple[str, int], asyncio.Lock] = defaultdict(asyncio.Lock)

    def labelled(self, repo: str, number: int) -> None:
        if (repo, number) not in self.seen:
            self.seen.add((repo, number))
            self._start(repo, number, None, forget=True)

    def comments(self, repo: str, comments: list[dict]) -> None:
        for c in new_agent_comments(comments, self.last_comment, repo):
            self._start(repo, c["number"], c["instructions"], forget=False)

    def _start(self, repo: str, number: int, instructions: str | None, forget: bool) -> None:
        async def job():
            async with self._locks[(repo, number)]:
                await self.run(repo, number, instructions)

        task = asyncio.create_task(job())
        self.tasks.add(task)

        def done(t: asyncio.Task) -> None:
            self.tasks.discard(t)
            if t.cancelled():
                return
            if t.exception() is None:
                if forget:
                    self.seen.discard((repo, number))
            else:  # a crashed run stays seen: no hot retry loop
                print(f"run for {repo}#{number} crashed: {t.exception()!r}", flush=True)

        task.add_done_callback(done)
