import os
import requests
from typing import Any, Dict, List


TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


def fetch_twitter_posts(query: str, limit: int, bearer_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "social-insights-poc/1.0",
    }
    params = {
        "query": query,
        "max_results": min(limit, 100),
        "tweet.fields": "created_at,lang,public_metrics",
    }
    response = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()

    tweets = []
    for item in payload.get("data", []):
        tweets.append(
            {
                "id": item.get("id"),
                "text": item.get("text", ""),
                "author": item.get("author_id"),
                "created_at": item.get("created_at"),
                "source": "twitter",
            }
        )
    return tweets
