import re

QUE_PATTERN = re.compile(r"\bque\b", re.IGNORECASE)


def _queue_matching_case(match: re.Match[str]) -> str:
    word = match.group(0)
    if word.isupper():
        return "QUEUE"
    if word[0].isupper():
        return "Queue"
    return "queue"


def fix_queue_spelling(text: str) -> str:
    """Correct the common misspelling "que" to "queue", keeping the original capitalization."""
    return QUE_PATTERN.sub(_queue_matching_case, text)
