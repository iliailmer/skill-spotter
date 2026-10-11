import json
import re
from pathlib import Path
from typing import Iterator

BLOCKS = re.compile(
    r"<(system-reminder|pasted_content|local-command-[a-z]+|command-[a-z]+)\b.*?</\1[^>]*>",
    re.S,
)
SKIP_PREFIXES = ("[Request interrupted", "Caveat:", "<", "Base directory for this skill")
MAX_LEN = 1500
MIN_LEN = 12


def clean_prompt(text: str) -> str:
    text = BLOCKS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith(SKIP_PREFIXES) or not (MIN_LEN <= len(text) <= MAX_LEN):
        return ""
    return text


def user_prompts(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (session, timestamp, text) for each real user prompt in a transcript."""
    with path.open(errors="ignore") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
                continue
            c = d.get("message", {}).get("content")
            if isinstance(c, list):
                c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            if not isinstance(c, str):
                continue
            text = clean_prompt(c)
            if text:
                yield d.get("sessionId") or path.stem, d.get("timestamp", ""), text
