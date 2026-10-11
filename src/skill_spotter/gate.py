from .index import Index, Match, tokens

MIN_TOKENS = 4
MIN_JACCARD = 0.35
MIN_SESSIONS = 2


def find_matches(index: Index, prompt: str, session: str | None) -> list[Match]:
    """Past prompts from at least two other sessions that look like this one. Empty list means no repeat."""
    qt = tokens(prompt)
    if len(qt) < MIN_TOKENS:
        return []
    found: dict[str, Match] = {}
    for text, sess in index.candidates(qt):
        if sess == session or text == prompt:
            continue
        pt = tokens(text)
        score = len(qt & pt) / len(qt | pt)
        if score >= MIN_JACCARD and (sess not in found or score > found[sess].score):
            found[sess] = Match(sess, text, score)
    if len(found) < MIN_SESSIONS:
        return []
    return sorted(found.values(), key=lambda m: -m.score)[:5]


def topic_key(prompt: str) -> str:
    return "-".join(sorted(tokens(prompt))[:4])
