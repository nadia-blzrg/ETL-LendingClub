"""
Centralized logger factory.
Each pipeline step gets its own named logger with file + console output.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from config.settings import LOGS_DIR


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a configured logger writing to:
      - stdout (INFO+)
      - logs/<name>_<date>.log (DEBUG+)
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:           # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ──────────────────────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # ── File handler ─────────────────────────────────────────────────────────
    log_file = LOGS_DIR / f"{name}_{datetime.now():%Y%m%d}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
