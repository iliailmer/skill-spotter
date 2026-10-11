import os
from pathlib import Path

GUARD = "SKILL_SPOTTER_ACTIVE"


def home() -> Path:
    p = Path(os.environ.get("SKILL_SPOTTER_HOME", "~/.cache/skill-spotter")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def projects() -> Path:
    return Path(os.environ.get("SKILL_SPOTTER_PROJECTS", "~/.claude/projects")).expanduser()
