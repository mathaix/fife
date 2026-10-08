"""Create the demo issues in a repo (`--repo owner/name`). `--label` labels them `agent` right away; `--reset` cleans up a previous run first."""

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


async def main(repo: str, label: bool, reset: bool):
    if reset:
        for pr in await gh.open_agent_prs(repo):
            await gh.close_pr_and_branch(repo, pr)
            print(f"closed PR #{pr['number']}")
        await gh.delete_media_branches(repo)
        for name in gh.LABELS:
            for issue in await gh.labelled_issues(repo, name):
                await gh.close_issue(repo, issue["number"])
                print(f"closed issue #{issue['number']}")
    await gh.ensure_labels(repo)
    for title, body in ISSUES:
        issue = await gh.create_issue(repo, title, body, ["agent"] if label else [])
        print(f"#{issue['number']} {title}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, metavar="OWNER/NAME")
    parser.add_argument("--label", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.repo, args.label, args.reset))
