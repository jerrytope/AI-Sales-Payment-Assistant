"""
Development settings — extends base.py.
Used for local development with DEBUG=True.
"""

from .base import *  # noqa: F401, F403

# Development-specific overrides
DEBUG = True

CORS_ALLOW_ALL_ORIGINS = True

# Show all SQL queries in console (optional — uncomment to enable)
# LOGGING["loggers"]["django.db.backends"] = {
#     "handlers": ["console"],
#     "level": "DEBUG",
#     "propagate": False,
# }
