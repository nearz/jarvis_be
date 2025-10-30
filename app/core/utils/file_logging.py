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
