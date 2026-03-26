"""
WSGI config for movie_booking_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import logging
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_booking_system.settings')

application = get_wsgi_application()

logger = logging.getLogger(__name__)


def _bootstrap_superuser():
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    if not username or not password:
        logger.info("Skipping automatic superuser bootstrap: username/password env vars are not set.")
        return

    try:
        from create_admin import create_admin

        logger.info("Running automatic superuser bootstrap for %s.", username)
        create_admin()
    except Exception:
        logger.exception(
            "Automatic superuser bootstrap failed during startup."
        )


_bootstrap_superuser()
