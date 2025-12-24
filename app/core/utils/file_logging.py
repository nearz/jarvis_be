import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)

# Path for failed persistence log file
FAILED_PERSISTENCE_LOG = Path(settings.LOG_DIR) / "failed_persistence.jsonl"


def log_failed_persistence(
    thread_id: str,
    user_id: str,
    llm: str,
    new_thread: bool,
    error: Exception,
    error_type: str,
    checkpoint_db_path: str = "checkpoints.db",
) -> None:
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "thread_id": thread_id,
            "user_id": user_id,
            "llm": llm,
            "new_thread": new_thread,
            "error_type": error_type,
            "error_class": type(error).__name__,
            "error_message": str(error),
            "recovery_note": (
                f"Data exists in checkpoint DB ({checkpoint_db_path}) under thread_id={thread_id}. "
                f"Query checkpoint database to retrieve messages and manually insert into app DB."
            ),
        }

        # Ensure the log directory exists
        FAILED_PERSISTENCE_LOG.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL file (one JSON object per line)
        with open(FAILED_PERSISTENCE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.info(
            "Failed persistence logged to file | thread_id: %s | file: %s",
            thread_id,
            FAILED_PERSISTENCE_LOG,
        )

    except Exception as log_error:
        # If logging to file fails, log to stderr as last resort
        logger.critical(
            "FAILED TO LOG FAILED PERSISTENCE | thread_id: %s | "
            "original_error: %s | logging_error: %s",
            thread_id,
            str(error),
            str(log_error),
        )


def read_failed_persistence_log(
    filter_user_id: Optional[str] = None,
    filter_error_type: Optional[str] = None,
) -> list[dict]:

    if not FAILED_PERSISTENCE_LOG.exists():
        return []

    entries = []

    try:
        with open(FAILED_PERSISTENCE_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Apply filters
                    if filter_user_id and entry.get("user_id") != filter_user_id:
                        continue
                    if (
                        filter_error_type
                        and entry.get("error_type") != filter_error_type
                    ):
                        continue

                    entries.append(entry)

                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse log entry: %s", str(e))
                    continue

        return entries

    except Exception as e:
        logger.error("Failed to read failed persistence log: %s", str(e))
        return []


def count_failed_persistence() -> int:
    if not FAILED_PERSISTENCE_LOG.exists():
        return 0

    try:
        with open(FAILED_PERSISTENCE_LOG, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        logger.error("Failed to count log entries: %s", str(e))
        return 0


# Path for Tavily search log file
TAVILY_SEARCH_LOG = (
    Path(settings.LOG_DIR) / settings.TAVILY_LOG_DIR / "tavily_searches.jsonl"
)


def log_tavily_search(
    query: str,
    results: list[dict],
    result_count: int,
) -> None:
    """
    Log Tavily search results to a JSONL file for inspection.

    Args:
        query: The search query string
        results: The raw results from Tavily API
        result_count: Number of results returned
    """
    if not settings.TAVILY_LOG_ENABLED:
        return

    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": query,
            "result_count": result_count,
            "results": results,
        }

        TAVILY_SEARCH_LOG.parent.mkdir(parents=True, exist_ok=True)

        with open(TAVILY_SEARCH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as log_error:
        logger.warning("Failed to log Tavily search: %s", str(log_error))
