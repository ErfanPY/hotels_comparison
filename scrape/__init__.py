from logging.config import dictConfig

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'console_print': {
            'format': '[%(levelname)s] %(asctime)s -- %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'formatter': 'console_print',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  
        },
        'file': {
            'level': 'ERROR',
            'formatter': 'console_print',
            'class': 'logging.FileHandler',
            'filename': 'logs/log.log',
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['default', 'file'],
            'level': 'WARNING',
            'propagate': False
        },
        '__main__': { 
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}

dictConfig(LOGGING_CONFIG)
