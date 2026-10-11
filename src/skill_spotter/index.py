import re
import sqlite3
from dataclasses import dataclass

from . import paths
from .transcripts import user_prompts

STOP = set(
    "the and for that this with from have has had are was were you your can could would should will "
    "not but all any out about into over then than them they their there here what when where which "
    "who why how its it's i'm i'd let's lets just like also want need please make use using ok okay "
    "yeah yes now too one two get got give show see look try some more less very much does did done "
    "dont don't isnt isn't doesnt doesn't thats that's".split()
)
TOKEN = re.compile(r"[a-z][a-z0-9_\-]{2,}")


def tokens(text: str) -> set[str]:
    return {t for t in TOKEN.findall(text.lower()) if t not in STOP}


@dataclass
class Match:
    session: str
    text: str
    score: float


class Index:
    def __init__(self, path=None):
        self.db = sqlite3.connect(path or paths.home() / "prompts.db", timeout=15)
        self.db.execute(
            "create virtual table if not exists p using fts5("
            "text, session UNINDEXED, ts UNINDEXED, tokenize='porter unicode61')"
        )
        self.db.execute("create table if not exists files(path text primary key, mtime real, size int)")

    def sync(self, root=None) -> int:
        """Re-read transcripts that changed since the last run. Returns files updated."""
        root = root or paths.projects()
        n = 0
        for f in root.glob("*/*.jsonl"):
            st = f.stat()
            row = self.db.execute("select mtime, size from files where path=?", (str(f),)).fetchone()
            if row == (st.st_mtime, st.st_size):
                continue
            self.db.execute("delete from p where session=?", (f.stem,))
            self.db.executemany(
                "insert into p(text, session, ts) values (?,?,?)",
                [(t, s, ts) for s, ts, t in user_prompts(f)],
            )
            self.db.execute("insert or replace into files values (?,?,?)", (str(f), st.st_mtime, st.st_size))
            n += 1
        self.db.commit()
        return n

    def candidates(self, query_tokens: set[str], limit: int = 30):
        q = " OR ".join(f'"{t}"' for t in sorted(query_tokens)[:14])
        return self.db.execute(
            "select text, session from p where p match ? order by bm25(p) limit ?", (q, limit)
        ).fetchall()
