import argparse
import os
import sys
from ingest import ingest_file, ingest_twitter
from processing import build_trending_topics, get_sentiment_summary
from cleaner import clean_posts
from storage import InsightStorage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Social media insights POC: ingest from file or Twitter API, process trending topics."
    )
    parser.add_argument(
        "--mode",
        choices=["file", "twitter", "daemon"],
        required=True,
        help="Data ingestion source: file, twitter, or daemon (continuous scheduler).",
    )
    parser.add_argument(
        "--file",
        help="Path to a local JSON or CSV file with posts.",
    )
    parser.add_argument(
        "--query",
        help="Twitter search query for ingestion.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of posts to ingest.",
    )
    parser.add_argument(
        "--db",
        default="data/social_insights.db",
        help="SQLite database file path.",
    )
    parser.add_argument(
        "--watch-folder",
        default="data/incoming",
        help="Folder to watch for new files (daemon mode).",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Twitter poll interval in seconds (daemon mode).",
    )
    args = parser.parse_args()

    if args.mode == "daemon":
        from scheduler_app import SchedulerApp
        app = SchedulerApp(watch_folder_path=args.watch_folder, db_path=args.db)
        app.start(enable_file_watch=True, enable_twitter_poll=True, poll_interval=args.poll_interval)
        return

    storage = InsightStorage(db_path=args.db)
    storage.initialize()

    if args.mode == "file":
        if not args.file:
            raise SystemExit("--file is required when --mode=file")
        posts = ingest_file(args.file)
    else:
        if not args.query:
            raise SystemExit("--query is required when --mode=twitter")
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        posts = ingest_twitter(args.query, limit=args.limit, bearer_token=bearer_token)

    if not posts:
        raise SystemExit("No posts were ingested. Check the source and inputs.")

    storage.save_posts(posts)

    cleaned_posts_list = clean_posts(posts)
    storage.save_cleaned_posts(cleaned_posts_list)

    trending = build_trending_topics(cleaned_posts_list, top_n=20)
    sentiment = get_sentiment_summary(cleaned_posts_list)
    storage.save_trending_topics(trending, source=args.mode)

    print("\nIngested posts:\n")
    for post in cleaned_posts_list[:5]:
        print(f"- [{post['id']}] {post['text'][:120]}")

    print("\nSentiment Analysis:\n")
    print(f"Positive: {sentiment.get('positivePercent', 0)}%")
    print(f"Negative: {sentiment.get('negativePercent', 0)}%")
    print(f"Neutral: {100 - sentiment.get('positivePercent', 0) - sentiment.get('negativePercent', 0)}%")

    print("\nTrending topics:\n")
    for rank, topic in enumerate(trending, start=1):
        print(f"{rank}. {topic['topic']} ({topic['count']})")

    print(f"\nResults stored in: {args.db}")


if __name__ == "__main__":
    main()
