"""
logger.py — Coloured console + file logging for the bot.
"""

import logging
import os
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

LOG_DIR  = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log")


class ColouredFormatter(logging.Formatter):
    COLOURS = {
        logging.DEBUG:    Fore.CYAN,
        logging.INFO:     Fore.GREEN,
        logging.WARNING:  Fore.YELLOW,
        logging.ERROR:    Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def format(self, record):
        colour = self.COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname:<8}{Style.RESET_ALL}"
        return super().format(record)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("upstox_bot")
    logger.setLevel(logging.DEBUG)

    fmt = "%(asctime)s  %(levelname)s %(message)s"
    datefmt = "%H:%M:%S"

    # Console handler (coloured)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColouredFormatter(fmt, datefmt=datefmt))
    logger.addHandler(ch)

    # File handler (plain text)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    logger.addHandler(fh)

    return logger


log = _build_logger()
