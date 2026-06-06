import argparse
import logging
import os
import sys
from pathlib import Path

from cleaner import clean_posts
from ingest import ingest_file, ingest_twitter
from processing import build_trending_topics, get_sentiment_summary
from scheduler import Scheduler, watch_folder
from storage import InsightStorage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SchedulerApp:
    def __init__(self, watch_folder_path: str, db_path: str = "data/social_insights.db"):
        self.watch_folder_path = watch_folder_path
        self.storage = InsightStorage(db_path=db_path)
        self.storage.initialize()
        self.scheduler = Scheduler()
        self.file_observer = None

    def on_file_created(self, file_path: str) -> None:
        """Callback when a new file is detected in the watch folder."""
        try:
            logger.info(f"Ingesting file: {file_path}")
            posts = ingest_file(file_path)
            if not posts:
                logger.warning(f"No data ingested from {file_path}")
                return

            self.storage.save_posts(posts)
            logger.info(f"Saved {len(posts)} raw posts from {file_path}")

            unprocessed = self.storage.load_unprocessed_raw_posts()
            if unprocessed:
                cleaned = clean_posts(unprocessed)
                self.storage.save_cleaned_posts(cleaned)
                logger.info(f"Cleaned and saved {len(cleaned)} posts")

                trending = build_trending_topics(cleaned, top_n=20)
                sentiment = get_sentiment_summary(cleaned)
                self.storage.save_trending_topics(trending, source=Path(file_path).name)
                logger.info(f"Updated trending topics. Sentiment: {sentiment}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)

    def on_twitter_poll(self) -> None:
        """Callback for periodic Twitter polling."""
        try:
            query = os.getenv("TWITTER_QUERY", "insurance")
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

            if not bearer_token:
                logger.debug("TWITTER_BEARER_TOKEN not set, skipping Twitter poll")
                return

            logger.info(f"Polling Twitter for: {query}")
            posts = ingest_twitter(query, limit=50, bearer_token=bearer_token)
            if not posts:
                logger.info("No new tweets found")
                return

            self.storage.save_posts(posts)
            logger.info(f"Saved {len(posts)} tweets")

            unprocessed = self.storage.load_unprocessed_raw_posts()
            if unprocessed:
                cleaned = clean_posts(unprocessed)
                self.storage.save_cleaned_posts(cleaned)
                logger.info(f"Cleaned and saved {len(cleaned)} posts")

                trending = build_trending_topics(cleaned, top_n=20)
                sentiment = get_sentiment_summary(cleaned)
                self.storage.save_trending_topics(trending, source="twitter")
                logger.info(f"Updated trending topics from Twitter. Sentiment: {sentiment}")

        except Exception as e:
            logger.error(f"Error during Twitter poll: {e}", exc_info=True)

    def start(self, enable_file_watch: bool = True, enable_twitter_poll: bool = True, poll_interval: int = 60) -> None:
        """Start the scheduler app."""
        logger.info("=" * 60)
        logger.info("SCHEDULER APP STARTED")
        logger.info("=" * 60)

        if enable_file_watch:
            self.file_observer = watch_folder(self.watch_folder_path, self.on_file_created)
            if self.file_observer:
                logger.info(f"File watching enabled on: {self.watch_folder_path}")

        if enable_twitter_poll:
            self.scheduler.schedule_interval(
                self.on_twitter_poll,
                interval_seconds=poll_interval,
                name="twitter_poll",
            )
            logger.info(f"Twitter polling enabled every {poll_interval}s")

        try:
            self.scheduler.run_forever()
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            if self.file_observer:
                self.file_observer.stop()
                self.file_observer.join()
            logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.running = False
        if self.file_observer:
            self.file_observer.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Social media insights scheduler: watch files and poll Twitter continuously."
    )
    parser.add_argument(
        "--watch-folder",
        default="data/incoming",
        help="Folder to watch for new files (default: data/incoming)",
    )
    parser.add_argument(
        "--twitter-poll",
        action="store_true",
        default=True,
        help="Enable Twitter polling (default: True)",
    )
    parser.add_argument(
        "--no-twitter-poll",
        dest="twitter_poll",
        action="store_false",
        help="Disable Twitter polling",
    )
    parser.add_argument(
        "--file-watch",
        action="store_true",
        default=True,
        help="Enable file watching (default: True)",
    )
    parser.add_argument(
        "--no-file-watch",
        dest="file_watch",
        action="store_false",
        help="Disable file watching",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Twitter poll interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--db",
        default="data/social_insights.db",
        help="SQLite database file path",
    )
    args = parser.parse_args()

    app = SchedulerApp(watch_folder_path=args.watch_folder, db_path=args.db)
    app.start(
        enable_file_watch=args.file_watch,
        enable_twitter_poll=args.twitter_poll,
        poll_interval=args.poll_interval,
    )


if __name__ == "__main__":
    main()
