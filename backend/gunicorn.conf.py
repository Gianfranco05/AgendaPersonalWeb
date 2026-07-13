import multiprocessing
import os

import logging
from pythonjsonlogger import jsonlogger

# Workers
cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", str(2 * cpu_count + 1)))

timeout = 120
graceful_timeout = 30
preload_app = True

worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"

# Logging
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": jsonlogger.JsonFormatter,
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
            "timestamp": True,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": os.getenv("LOG_LEVEL", "INFO").upper(),
        "handlers": ["console"],
    },
    "loggers": {
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
