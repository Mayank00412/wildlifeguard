import logging
import sys
from typing import Optional


def configure_logging(level: str = "INFO") -> None:
    """Configure structured-enough console logging for the API process."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(numeric_level)
        for handler in root.handlers:
            handler.setLevel(numeric_level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(numeric_level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "wildlifeguard")
