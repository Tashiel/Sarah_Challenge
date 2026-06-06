import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case or space-separated strings to camelCase."""
    components = re.split(r'[\s_-]+', snake_str.lower())
    return components[0] + ''.join(x.title() for x in components[1:])


def trim_string(value: Any) -> Optional[str]:
    """Trim whitespace and handle None values."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def parse_date(date_str: Any) -> Optional[str]:
    """
    Parse various date formats and return as dd-mm-yyyy.
    Returns None if unparseable.
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()
    if not date_str:
        return None

    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue

    return None


def analyze_sentiment(text: str) -> tuple[str, float]:
    """
    Analyze sentiment of text using TextBlob or return neutral if unavailable.
    Returns (sentiment_label, polarity_score)
    """
    if not HAS_TEXTBLOB:
        return ("neutral", 0.0)

    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return ("positive", polarity)
        elif polarity < -0.1:
            return ("negative", polarity)
        else:
            return ("neutral", polarity)
    except Exception:
        return ("neutral", 0.0)


def clean_post(raw_post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a raw post:
    - Trim all string values
    - Convert field names to camelCase
    - Parse dates to dd-mm-yyyy
    - Analyze sentiment
    - Handle nulls
    """
    text = trim_string(raw_post.get("text"))
    if not text:
        return {}

    author = trim_string(raw_post.get("author"))
    source = trim_string(raw_post.get("source"))
    created_at = parse_date(raw_post.get("created_at"))

    sentiment, sentiment_score = analyze_sentiment(text)

    return {
        "id": raw_post.get("id"),
        "text": text,
        "author": author or "unknown",
        "createdAt": created_at,
        "source": source or "unknown",
        "sentiment": sentiment,
        "sentimentScore": sentiment_score,
    }


def clean_posts(raw_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean a batch of raw posts."""
    cleaned = []
    seen_ids = set()

    for raw in raw_posts:
        post_id = str(raw.get("id") or "")
        if not post_id or post_id in seen_ids:
            continue

        cleaned_post = clean_post(raw)
        if cleaned_post:
            seen_ids.add(post_id)
            cleaned.append(cleaned_post)

    return cleaned
