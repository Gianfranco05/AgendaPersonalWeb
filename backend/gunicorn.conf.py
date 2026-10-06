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

# IP real del cliente detras de nginx. Sin esto gunicorn solo confia en
# X-Forwarded-For si viene de 127.0.0.1, y nginx esta en otro contenedor: el
# backend veria a todos con la IP de nginx y los rate limits (login, boton de
# arrepentimiento) serian un unico balde compartido por todo el mundo.
# "*" es seguro porque el backend no publica puertos (solo nginx lo alcanza) y
# nginx pisa X-Forwarded-For con $remote_addr: con "*" uvicorn toma el primer
# valor del header, que sin ese pisado lo podria inventar el cliente. Si algun
# dia hay un CDN adelante (p. ej. Cloudflare), $remote_addr pasa a ser el CDN y
# hay que tomar la IP de su header (CF-Connecting-IP) en nginx.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")

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
