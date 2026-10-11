"""Where accepted suggestions are written. Uses a chezmoi source tree when there is one."""
import os
import subprocess
from pathlib import Path


def chezmoi_source() -> Path | None:
    if os.environ.get("SKILL_SPOTTER_SOURCE"):
        return Path(os.environ["SKILL_SPOTTER_SOURCE"])
    try:
        out = subprocess.run(["chezmoi", "source-path"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None


def skills_dir() -> Path:
    if os.environ.get("SKILL_SPOTTER_SKILLS_DIR"):
        return Path(os.environ["SKILL_SPOTTER_SKILLS_DIR"])
    src = chezmoi_source()
    if src and (src / "dot_claude").is_dir():
        return src / "dot_claude" / "skills"
    return Path("~/.claude/skills").expanduser()


def rules_file() -> Path:
    if os.environ.get("SKILL_SPOTTER_RULES_FILE"):
        return Path(os.environ["SKILL_SPOTTER_RULES_FILE"])
    src = chezmoi_source()
    if src:
        for rel in ("dot_claude/CLAUDE.md", "dot_codex/AGENTS.md"):
            if (src / rel).is_file():
                return src / rel
    return Path("~/.claude/CLAUDE.md").expanduser()


def existing_skills() -> list[str]:
    bases = {skills_dir(), Path("~/.claude/skills").expanduser()}
    return sorted({p.name for b in bases if b.is_dir() for p in b.iterdir() if p.is_dir()})


def read_rules() -> str:
    for p in (rules_file(), Path("~/.claude/CLAUDE.md").expanduser()):
        try:
            return p.read_text()
        except OSError:
            continue
    return ""
