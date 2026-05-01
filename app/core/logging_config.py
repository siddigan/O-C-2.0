from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.settings import settings

LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging() -> Path:
    global _configured

    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if _configured:
        return log_path

    root_logger = logging.getLogger()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler_exists = False
    stream_handler_exists = False

    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == log_path.resolve():
            file_handler_exists = True
        elif type(handler) is logging.StreamHandler:
            stream_handler_exists = True

    if not file_handler_exists:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if not stream_handler_exists:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _configured = True
    return log_path


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def read_recent_logs(limit: int = 200, level: str | None = None) -> list[dict[str, str]]:
    log_path = setup_logging()
    if not log_path.exists():
        return []

    selected_level = level.upper() if level else None
    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries: list[dict[str, str]] = []

    for line in lines[-limit * 4 :]:
        parts = line.split("|", 3)
        if len(parts) == 4:
            timestamp, entry_level, logger_name, message = parts
        else:
            timestamp, entry_level, logger_name, message = "", "INFO", "unknown", line

        if selected_level and entry_level != selected_level:
            continue

        entries.append(
            {
                "timestamp": timestamp,
                "level": entry_level,
                "logger": logger_name,
                "message": message,
            }
        )

    return entries[-limit:]
