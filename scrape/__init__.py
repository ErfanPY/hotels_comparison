from logging.config import dictConfig
import os

main_logger_level = 'DEBUG' if os.environ.get("SCRAPPER_DEBUG") == "1" else 'INFO'

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'default_fromatter': {
            'format': '[%(levelname)s] %(asctime)s -- %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'default_fromatter',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  
        },
        'email': {
            'level': 'CRITICAL',
            'formatter': 'default_fromatter',
            'class': 'logging.handlers.SMTPHandler',
            'mailhost': [
                os.environ.get("EMAIL_HOST"),
                int(os.environ.get("EMAIL_PORT", "0"))
            ],
            'fromaddr': os.environ.get("EMAIL_USER_ADDR"),
            'toaddrs': os.environ.get("EMAIL_TO_ADDR", "").split(","),
            'credentials': [
                os.environ.get("EMAIL_USER_ADDR"),
                os.environ.get("EMAIL_PASSWORD")
            ],
            'subject': 'Alibaba scrapper critical error.',
            'secure': []
        },
        'rotatingFile': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'default_fromatter',
            'filename': 'error.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        }
    },
    'loggers': {
        'main_logger': {
            'handlers': ['default', 'rotatingFile'],
            'level': main_logger_level,
            'propagate': False
        },
        'email_logger': {
            'handlers': ['email', 'default', 'rotatingFile'],
            'level': 'CRITICAL',
            'propagate': False
        }
    }
}

dictConfig(LOGGING_CONFIG)
