"""Create the demo issues in the repo. `--label` labels them `agent` right away; `--reset` cleans up a previous run first."""

import argparse
import asyncio

import gh

ISSUES = [
    (
        "Pagination returns one book too many",
        "`GET /books?page=1&size=2` returns 3 books, and the last one is repeated as the first book of page 2. "
        "Each page should contain exactly `size` books with no overlap.",
    ),
    (
        "Add a health check endpoint",
        'Add `GET /health` that returns `{"status": "ok"}` with a 200, so the deploy platform can probe the service.',
    ),
    (
        "Reject books published in the future",
        "`POST /books` accepts any `year`. Return a 422 validation error when `year` is later than the current year.",
    ),
]
LABELS = {"agent": "5319e7", "agent-working": "fbca04", "agent-done": "0e8a16", "agent-failed": "d93f0b"}


async def main(label: bool, reset: bool):
    if reset:
        for pr in await gh.open_agent_prs():
            await gh.close_pr_and_branch(pr)
            print(f"closed PR #{pr['number']}")
        for name in LABELS:
            for issue in await gh.labelled_issues(name):
                await gh.close_issue(issue["number"])
                print(f"closed issue #{issue['number']}")
    for name, color in LABELS.items():
        await gh.ensure_label(name, color)
    for title, body in ISSUES:
        issue = await gh.create_issue(title, body, ["agent"] if label else [])
        print(f"#{issue['number']} {title}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.label, args.reset))
