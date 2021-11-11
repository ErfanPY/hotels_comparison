import os
import logging

logger = logging.getLogger("email_logger")


def log_critical_error(text):
    
    if not os.environ.get("DO_SEND_EMAIL") == "1":
        logger.error("email skiped, "+text)
    
    
    logger.critical(text)
