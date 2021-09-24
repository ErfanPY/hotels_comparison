from logging.config import dictConfig

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
            'level': 'DEBUG',
            'formatter': 'default_fromatter',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  
        },
        'file': {
            'level': 'ERROR',
            'formatter': 'default_fromatter',
            'class': 'logging.FileHandler',
            'filename': 'log.log',
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
            'level': 'ERROR',
            'propagate': False
        },
        '__main__': { 
            'handlers': ['default', 'rotatingFile'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}

dictConfig(LOGGING_CONFIG)
