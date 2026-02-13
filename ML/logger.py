"""
Logger — Structured Logging Setup for AI Office Chain.

Creates a timestamped log file under ML/logs/ and configures
Python's logging module for both file and console output.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


# ── Log directory ────────────────────────────────────────────────
LOGS_DIR = Path(__file__).resolve().parent / "logs"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Initialize structured logging with file + console handlers.

    Creates a log file at ML/logs/{timestamp}.log.
    Returns the root 'office_chain' logger.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{timestamp}.log"

    logger = logging.getLogger("office_chain")
    logger.setLevel(level)

    # Prevent duplicate handlers on re-init
    if logger.handlers:
        logger.handlers.clear()

    # ── File handler (detailed) ──────────────────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)
    logger.addHandler(fh)

    # ── Console handler (minimal, only warnings+) ────────────────
    console_fmt = logging.Formatter(
        fmt="  %(levelname)s: %(message)s",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(console_fmt)
    logger.addHandler(ch)

    logger.info(f"Logging initialized — file: {log_file}")
    return logger


def get_logger(name: str = "office_chain") -> logging.Logger:
    """Get a child logger under the office_chain namespace."""
    return logging.getLogger(f"office_chain.{name}")
