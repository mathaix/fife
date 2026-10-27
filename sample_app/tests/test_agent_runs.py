"""The issue agent's pure logic: `/agent` comment parsing, run records, the `seen` reset and the resume fallback."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
import runs  # noqa: E402


def comment(id, body, number=3, assoc="COLLABORATOR", user_type="User"):
    return {
        "id": id, "body": body, "author_association": assoc, "user": {"type": user_type},
        "issue_url": f"https://api.github.com/repos/o/r/issues/{number}",
    }  # fmt: skip


def test_parse_agent_comment():
    assert runs.parse_agent_comment("/agent make it blue") == "make it blue"
    assert runs.parse_agent_comment("  /agent\nline one\nline two") == "line one\nline two"
    assert runs.parse_agent_comment("/agent") == ""
    for body in ["thanks!", "please /agent do it", "/agentic stuff", "", None]:
        assert runs.parse_agent_comment(body) is None


def test_only_trusted_humans_trigger_and_ordinary_comments_do_not():
    last = {}
    found = runs.new_agent_comments(
        [comment(1, "looks good"), comment(2, "/agent a", assoc="NONE"), comment(3, "/agent b", user_type="Bot"), comment(4, "/agent c", assoc="OWNER")],
        last, "o/r",
    )  # fmt: skip
    assert [(c["id"], c["instructions"]) for c in found] == [(4, "c")]
    assert last[("o/r", 3)] == 4


def test_last_seen_comment_id_is_per_issue_and_not_retriggered():
    last = {}
    batch = [comment(5, "/agent x", number=3), comment(6, "/agent y", number=4)]
    assert [c["number"] for c in runs.new_agent_comments(batch, last, "o/r")] == [3, 4]
    assert runs.new_agent_comments(batch + [comment(7, "/agent z", number=3)], last, "o/r") == [{"number": 3, "instructions": "z", "id": 7}]


def test_branch_and_session_keys():
    assert runs.issue_number_from_branch("agent/issue-12") == 12
    assert runs.issue_number_from_branch("feature/x") is None
    assert runs.session_key("o/r", 3, "abc") == "o/r/issue-3/abc.jsonl"


def test_record_names_stage_reason_and_volume_session():
    rec = runs.Record(status="failed", stage="push", reason="rejected", rounds=2, cost=0.5, sandbox="sb-1", session="o/r/issue-3/abc.jsonl")
    text = runs.render_record(rec, "agent-sessions")
    assert runs.RECORD_MARKER in text
    for part in ["push (failed here)", "rejected", "$0.500", "sb-1", "o/r/issue-3/abc.jsonl", "agent-sessions", "Re-add the `agent` label"]:
        assert part in text


def test_failed_push_diff_is_attached_and_truncated():
    assert "+hello" in runs.diff_comment("+hello", "the push failed")
    assert "truncated" in runs.diff_comment("x" * (runs.MAX_COMMENT_DIFF + 1), "the push failed")


def test_fallback_prompt_has_issue_pr_diff_and_instructions():
    prompt = runs.fallback_prompt({"number": 3, "title": "T", "body": "B"}, "PR summary", "+added line", "make it blue")
    for part in ["#3", "T", "B", "PR summary", "+added line", "make it blue"]:
        assert part in prompt


def test_label_retry_clears_seen_after_a_finished_run():
    async def scenario():
        runs_started = []

        async def run(repo, number, instructions):
            runs_started.append((number, instructions))

        d = runs.Dispatcher(run)
        d.labelled("o/r", 3)
        d.labelled("o/r", 3)  # still seen: no second run
        await asyncio.gather(*d.tasks)
        await asyncio.sleep(0)
        assert ("o/r", 3) not in d.seen
        d.labelled("o/r", 3)  # `agent` re-added after agent-failed
        await asyncio.gather(*d.tasks)
        return runs_started

    assert asyncio.run(scenario()) == [(3, None), (3, None)]


def test_crashed_run_stays_seen_so_it_does_not_retry_in_a_loop():
    async def scenario():
        async def run(repo, number, instructions):
            raise RuntimeError("boom")

        d = runs.Dispatcher(run)
        d.labelled("o/r", 3)
        await asyncio.gather(*d.tasks, return_exceptions=True)
        await asyncio.sleep(0)
        return d.seen

    assert asyncio.run(scenario()) == {("o/r", 3)}


def test_agent_comments_on_one_issue_queue_instead_of_running_together():
    async def scenario():
        active, peak, order = 0, 0, []

        async def run(repo, number, instructions):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            order.append(instructions)
            active -= 1

        d = runs.Dispatcher(run)
        d.comments("o/r", [comment(1, "/agent first"), comment(2, "/agent second"), comment(3, "just a note")])
        await asyncio.gather(*d.tasks)
        return peak, order

    assert asyncio.run(scenario()) == (1, ["first", "second"])
