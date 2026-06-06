import logging
import os
import time
from pathlib import Path
from typing import Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

logger = logging.getLogger(__name__)


class FileWatcher(FileSystemEventHandler):
    """Watch a directory for new or moved files."""

    def __init__(self, callback: Callable[[str], None], extensions: list[str] | None = None):
        self.callback = callback
        self.extensions = extensions or [".json", ".csv", ".xlsx"]

    def _should_process(self, file_path: str) -> bool:
        return any(file_path.lower().endswith(ext) for ext in self.extensions)

    def on_created(self, event):
        if event.is_dir:
            return
        file_path = event.src_path
        if self._should_process(file_path):
            logger.info(f"New file detected: {file_path}")
            self.callback(file_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        file_path = event.dest_path
        if self._should_process(file_path):
            logger.info(f"Moved file detected: {file_path}")
            self.callback(file_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        if self._should_process(file_path):
            logger.debug(f"Modified file detected: {file_path}")
            self.callback(file_path)


class Scheduler:
    """Simple scheduler for recurring tasks."""

    def __init__(self):
        self.jobs = []
        self.running = False

    def schedule_interval(self, func: Callable, interval_seconds: int, name: str = None):
        """Schedule a function to run every N seconds."""
        job_name = name or func.__name__
        logger.info(f"Scheduled job '{job_name}' to run every {interval_seconds}s")
        self.jobs.append({"func": func, "interval": interval_seconds, "name": job_name, "last_run": 0})

    def run_once(self):
        """Execute all jobs that are due."""
        now = time.time()
        for job in self.jobs:
            if now - job["last_run"] >= job["interval"]:
                try:
                    logger.info(f"Running job: {job['name']}")
                    job["func"]()
                    job["last_run"] = now
                except Exception as e:
                    logger.error(f"Error in job {job['name']}: {e}")

    def run_forever(self):
        """Run scheduler loop indefinitely."""
        self.running = True
        logger.info("Scheduler started")
        try:
            while self.running:
                self.run_once()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped")
            self.running = False


def watch_folder(folder_path: str, callback: Callable[[str], None]) -> Observer | None:
    """
    Start watching a folder for new files.
    Returns the observer or None if watchdog is not available.
    """
    if not HAS_WATCHDOG:
        logger.warning("watchdog not installed. File watching disabled. Install with: pip install watchdog")
        return None

    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(FileWatcher(callback), str(folder), recursive=False)
    observer.start()
    logger.info(f"Watching folder: {folder}")

    # Process any existing files at startup in case they were dropped before the watcher started.
    for child in folder.iterdir():
        if child.is_file() and child.suffix.lower() in [".json", ".csv", ".xlsx"]:
            logger.info(f"Found existing file at startup: {child}")
            callback(str(child))

    return observer
