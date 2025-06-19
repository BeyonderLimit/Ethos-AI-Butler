
# utils/logger.py

import logging
from rich.logging import RichHandler

def get_logger(name="ethos"):
    logger = logging.getLogger(name)

    if not logger.hasHandlers():  # Prevent duplicate handlers
        logger.setLevel(logging.DEBUG)

        handler = RichHandler(rich_tracebacks=True, markup=True)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
