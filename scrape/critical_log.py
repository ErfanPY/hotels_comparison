import os
import logging
import socket
print()
logger = logging.getLogger("email_logger")


def log_critical_error(text):
    if os.environ.get("DONT_SEND_EMAIL") != "1":
        logger.critical(
            f"host: {socket.gethostname()}, {text}"
        )
    logger.exception("[CRITICAL] "+text)
