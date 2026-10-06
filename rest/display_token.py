"""Shared secret between the touchscreen (ttne-display) and this web app.

The display talks to Django over localhost without a login, so it sends this
token in the ``X-NE-Display-Token`` header. The token lives in a root-only file
on the PDU, which only the PDU's own processes can read. If the file is missing
or unreadable, display access is refused (fail closed).
"""
import hmac
import logging
import os
import secrets

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

TOKEN_PATH = os.path.join('/home', 'root', '.ne', 'display_token')
HEADER_META_KEY = 'HTTP_X_NE_DISPLAY_TOKEN'


def ensure_display_token(path: str = TOKEN_PATH) -> None:
    """Create the token file once, with a random value, if it does not exist."""
    if os.path.exists(path):
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(32) + '\n')
    except FileExistsError:
        pass
    except OSError as ex:
        logger.error('Could not create display token at %s: %s', path, ex)


def load_display_token(path: str = TOKEN_PATH) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ''


class DisplayTokenOrAuthenticated(BasePermission):
    """Lets a logged-in user, or the touchscreen holding the device token, through."""

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        expected = load_display_token()
        given = request.META.get(HEADER_META_KEY, '')
        return bool(expected) and hmac.compare_digest(given, expected)
