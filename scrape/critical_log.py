import os
import logging

logger = logging.getLogger("email_logger")


def log_critical_error(text):

    if os.environ.get("DONT_SEND_EMAIL") == "1":
        logger.error("[CRITICAL] email skiped, "+text)
    else:
        logger.critical(text, stack_info=True)
