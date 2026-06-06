import re
from collections import Counter
from typing import Any, Dict, Iterable, List

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "are", "was", "were", "from",
    "what", "when", "where", "how", "have", "has", "had", "not", "but", "you",
    "your", "our", "they", "them", "about", "over", "under", "more", "can", "will",
    "just", "like", "get", "got", "good", "great", "would", "could", "should",
    "insurance", "policy", "claim", "claims", "customer", "cover", "covers", "covered",
}

WORD_PATTERN = re.compile(r"#?([A-Za-z0-9_]{2,})")


def clean_text(text: str) -> str:
    text = text.strip().replace("\n", " ")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def build_trending_topics(posts: List[Dict[str, Any]], top_n: int = 20) -> List[Dict[str, Any]]:
    """Extract trending topics from cleaned posts."""
    terms: Counter[str] = Counter()
    for post in posts:
        text = post.get("text", "")
        for match in WORD_PATTERN.findall(text):
            term = match.lower()
            if term in STOPWORDS or len(term) < 3:
                continue
            terms[term] += 1

    trending = [
        {"topic": topic, "count": count}
        for topic, count in terms.most_common(top_n)
    ]
    return trending


def get_sentiment_summary(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get sentiment statistics from cleaned posts."""
    if not posts:
        return {"positive": 0, "negative": 0, "neutral": 0}

    sentiments = Counter(post.get("sentiment", "neutral") for post in posts)
    total = len(posts)

    return {
        "positive": sentiments.get("positive", 0),
        "negative": sentiments.get("negative", 0),
        "neutral": sentiments.get("neutral", 0),
        "total": total,
        "positivePercent": round(100 * sentiments.get("positive", 0) / total, 2),
        "negativePercent": round(100 * sentiments.get("negative", 0) / total, 2),
    }


def summarize_posts(posts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Legacy method for backward compatibility. Now delegated to cleaner.py."""
    from cleaner import clean_posts
    return clean_posts(list(posts))
