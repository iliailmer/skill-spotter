import json
import os
import time
from pathlib import Path

from . import paths

COOLDOWN_DAYS = 7


def _file(name: str) -> Path:
    return paths.home() / name


def load_pending() -> list[dict]:
    try:
        return json.loads(_file("pending.json").read_text())
    except (OSError, ValueError):
        return []


def save_pending(items: list[dict]) -> None:
    tmp = _file("pending.json.tmp")
    tmp.write_text(json.dumps(items, indent=2))
    os.replace(tmp, _file("pending.json"))


def log_decision(**fields) -> None:
    fields["t"] = time.time()
    with _file("decisions.jsonl").open("a") as fh:
        fh.write(json.dumps(fields) + "\n")


def on_cooldown(key: str) -> bool:
    cutoff = time.time() - COOLDOWN_DAYS * 86400
    try:
        for line in _file("decisions.jsonl").read_text().splitlines():
            d = json.loads(line)
            if d.get("key") == key and d.get("stage") == "suggested" and d["t"] > cutoff:
                return True
    except (OSError, ValueError):
        pass
    return False
