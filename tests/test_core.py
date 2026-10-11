import json

from skill_spotter import gate, state
from skill_spotter.index import Index
from skill_spotter.transcripts import clean_prompt, user_prompts


def write_session(root, name, prompts):
    d = root / "proj"
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({"type": "user", "sessionId": name, "timestamp": "t", "message": {"content": p}})
        for p in prompts
    ]
    (d / f"{name}.jsonl").write_text("\n".join(lines))


def test_clean_prompt_drops_system_text():
    assert clean_prompt("<task-notification>x</task-notification>") == ""
    assert clean_prompt("hi") == ""
    assert clean_prompt("fix the sidebar <system-reminder>noise</system-reminder> colors please") == "fix the sidebar colors please"


def test_user_prompts_skips_tool_results(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text(
        json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}})
        + "\n"
        + json.dumps({"type": "user", "sessionId": "s", "message": {"content": "please bump the version now"}})
    )
    assert [t for _, _, t in user_prompts(f)] == ["please bump the version now"]


def test_gate_needs_two_other_sessions(tmp_path):
    root = tmp_path / "projects"
    text = "merge the stack and bump the version number"
    write_session(root, "a", [text])
    write_session(root, "b", ["after the stack merge, bump the version"])
    write_session(root, "c", ["completely unrelated question about lua plugins"])
    idx = Index(tmp_path / "p.db")
    idx.sync(root)
    assert len(gate.find_matches(idx, text + " again", "new")) == 2
    assert gate.find_matches(idx, "explain lua plugins loading order", "new") == []
    assert gate.find_matches(idx, text, "a") == []  # only one other session left


def test_cooldown_blocks_repeat_suggestion(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILL_SPOTTER_HOME", str(tmp_path))
    assert not state.on_cooldown("k")
    state.log_decision(stage="suggested", key="k")
    assert state.on_cooldown("k")


def test_accept_rule_appends_under_heading(tmp_path, monkeypatch):
    from skill_spotter import cli

    rules = tmp_path / "CLAUDE.md"
    rules.write_text("# Instructions\n")
    monkeypatch.setenv("SKILL_SPOTTER_HOME", str(tmp_path))
    monkeypatch.setenv("SKILL_SPOTTER_RULES_FILE", str(rules))
    state.save_pending([{"kind": "rule", "name": "few-tests", "description": "d", "body": "Write few tests.",
                         "prompt": "p", "matches": ["m"], "shown": True}])
    cli.cmd_accept("few-tests")
    assert rules.read_text().endswith("## Added by skill-spotter\n\n- Write few tests.\n")
    assert state.load_pending() == []


def test_accept_skill_writes_file(tmp_path, monkeypatch):
    from skill_spotter import cli

    monkeypatch.setenv("SKILL_SPOTTER_HOME", str(tmp_path))
    monkeypatch.setenv("SKILL_SPOTTER_SKILLS_DIR", str(tmp_path / "skills"))
    state.save_pending([{"kind": "skill", "name": "x-y", "description": "Use when x.", "body": "1. Do x.",
                         "prompt": "p", "matches": ["m"], "shown": True}])
    cli.cmd_accept("x-y")
    assert (tmp_path / "skills" / "x-y" / "SKILL.md").read_text().startswith("---\nname: x-y\n")
