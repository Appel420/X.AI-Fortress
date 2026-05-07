# Config.py — Centralized configuration module for SelfFixerDaemon
import os
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# --- SelfFixer Settings ---
SELF_FIXER_INITIAL_BACKOFF = float(os.getenv("SELF_FIXER_INITIAL_BACKOFF", 0.2))
SELF_FIXER_MAX_BACKOFF = float(os.getenv("SELF_FIXER_MAX_BACKOFF", 5.0))
SELF_FIXER_HEARTBEAT_FREQ = int(os.getenv("SELF_FIXER_HEARTBEAT_FREQ", 10))
SELF_FIXER_STATUS_FILE = os.getenv("SELF_FIXER_STATUS_FILE", "self_fixer_status.txt")
SELF_FIXER_HEARTBEAT_MAX_BACKOFF = int(os.getenv("SELF_FIXER_HEARTBEAT_MAX_BACKOFF", 10))
SELF_FIXER_IDLE_THRESHOLD = int(os.getenv("SELF_FIXER_IDLE_THRESHOLD", 5))
SELF_FIXER_LOG_MODE = os.getenv("SELF_FIXER_LOG_MODE", "file")  # 'file' or 'console'


# --- Logging Configuration ---
def configure_logging():
    logger = logging.getLogger("SelfFixerDaemon")
    logger.setLevel(logging.DEBUG)

    if SELF_FIXER_LOG_MODE == "console":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    else:
        info_handler = TimedRotatingFileHandler("self_fixer_info.log", when="midnight", interval=1, backupCount=7)
        info_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        info_handler.setLevel(logging.INFO)

        error_handler = TimedRotatingFileHandler("self_fixer_error.log", when="midnight", interval=1, backupCount=7)
        error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        error_handler.setLevel(logging.ERROR)

        debug_handler = TimedRotatingFileHandler("self_fixer_debug.log", when="midnight", interval=1, backupCount=7)
        debug_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        debug_handler.setLevel(logging.DEBUG)

        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(debug_handler)

    return logger
