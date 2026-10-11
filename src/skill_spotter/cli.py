import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import paths, state
from .gate import find_matches, topic_key
from .index import Index
from .judge import judge
from .transcripts import clean_prompt

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){0,2}$")


def chezmoi_source() -> Path:
    try:
        out = subprocess.run(["chezmoi", "source-path"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path("~/.local/share/chezmoi").expanduser()


def existing_skills() -> list[str]:
    names = set()
    for base in (Path("~/.claude/skills").expanduser(), chezmoi_source() / "dot_claude" / "skills"):
        if base.is_dir():
            names.update(p.name for p in base.iterdir() if p.is_dir())
    return sorted(names)


def cmd_check() -> None:
    if os.environ.get(paths.GUARD):
        return
    data = json.load(sys.stdin)
    prompt = clean_prompt(data.get("prompt", ""))
    if not prompt:
        return
    index = Index()
    index.sync()
    matches = find_matches(index, prompt, data.get("session_id"))
    if not matches:
        return
    key = topic_key(prompt)
    if state.on_cooldown(key):
        state.log_decision(stage="cooldown", key=key)
        return
    verdict = judge(prompt, matches, existing_skills())
    state.log_decision(
        stage="judged", key=key, prompt=prompt, matches=[m.text for m in matches], verdict=verdict
    )
    if not verdict or not (verdict["same_task"] and verdict["skill_opportunity"]):
        return
    if not NAME.match(verdict["name"]) or verdict["name"] in existing_skills():
        return
    pending = state.load_pending()
    if any(p["name"] == verdict["name"] for p in pending):
        return
    pending.append(
        {
            "name": verdict["name"],
            "description": verdict["description"],
            "body": verdict["body"],
            "prompt": prompt,
            "matches": [m.text for m in matches],
            "shown": False,
        }
    )
    state.save_pending(pending)
    state.log_decision(stage="suggested", key=key, name=verdict["name"])


def cmd_show() -> None:
    if os.environ.get(paths.GUARD):
        return
    pending = state.load_pending()
    fresh = [p for p in pending if not p["shown"]]
    if not fresh:
        return
    p = fresh[0]
    p["shown"] = True
    state.save_pending(pending)
    msg = (
        f"skill-spotter: you asked something like this in {len(p['matches']) + 1} sessions "
        f'(e.g. "{p["matches"][0][:90]}"). Suggested skill `{p["name"]}`: {p["description"]} '
        f"Save it: `skill-spotter accept {p['name']}`. Skip it: `skill-spotter dismiss {p['name']}`."
    )
    print(json.dumps({"systemMessage": msg}))


def cmd_status() -> None:
    pending = state.load_pending()
    if pending:
        print(f"skill idea: {pending[0]['name']}")


def cmd_list() -> None:
    for p in state.load_pending():
        print(f"{p['name']}: {p['description']}")


def cmd_accept(name: str) -> None:
    pending = state.load_pending()
    item = next((p for p in pending if p["name"] == name), None)
    if not item:
        sys.exit(f"no pending skill named {name}")
    target = chezmoi_source() / "dot_claude" / "skills" / name / "SKILL.md"
    if target.exists():
        sys.exit(f"{target} already exists")
    target.parent.mkdir(parents=True)
    target.write_text(f"---\nname: {name}\ndescription: {item['description']}\n---\n\n{item['body'].strip()}\n")
    state.save_pending([p for p in pending if p["name"] != name])
    print(f"wrote {target}\nReview it, then: chezmoi apply ~/.claude/skills/{name}\nNothing is committed.")


def cmd_dismiss(name: str) -> None:
    pending = state.load_pending()
    state.save_pending([p for p in pending if p["name"] != name])
    state.log_decision(stage="dismissed", name=name)


def cmd_replay() -> None:
    """Run the gate over all past prompts to see how often it would fire."""
    from .transcripts import user_prompts

    index = Index()
    index.sync()
    total = flagged = 0
    shown = 0
    for f in sorted(paths.projects().glob("*/*.jsonl")):
        for sess, _, text in user_prompts(f):
            total += 1
            m = find_matches(index, text, sess)
            if m:
                flagged += 1
                if shown < 12:
                    shown += 1
                    print(f"- {text[:100]}\n    ~ {m[0].text[:100]}  ({m[0].score:.2f}, {len(m)} sessions)")
    print(f"\nprompts={total} flagged={flagged} rate={flagged / max(total, 1):.1%}")


def main() -> None:
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "list"), sys.argv[2:]
    table = {
        "check": cmd_check, "show": cmd_show, "status": cmd_status, "list": cmd_list,
        "replay": cmd_replay, "accept": lambda: cmd_accept(args[0]), "dismiss": lambda: cmd_dismiss(args[0]),
    }
    if cmd not in table:
        sys.exit(f"usage: skill-spotter [{'|'.join(table)}]")
    table[cmd]()
