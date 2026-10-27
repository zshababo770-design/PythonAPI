"""
Flattrade Trading CLI

Reliability improvements:
- Validates session setup and API responses.
- Avoids printing secrets or exception details that may contain sensitive data.
- Validates numeric input and required identifiers.
- Prevents duplicate WebSocket start attempts while connecting.
- Handles malformed API responses more defensively.
- Keeps the existing menu and core trading functionality.

Requires the Flattrade NorenApiPy helper module available in your environment.
Credentials are read from:
    FLATTRADE_USER_ID
    FLATTRADE_USER_TOKEN
"""

import logging
import os
from decimal import Decimal, InvalidOperation
from threading import Event, Lock

from api_helper import NorenApiPy


# --------------------------------------
# Configuration
# --------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

USER_ID = os.getenv("FLATTRADE_USER_ID", "").strip()
USER_TOKEN = os.getenv("FLATTRADE_USER_TOKEN", "").strip()

api = NorenApiPy()

socket_opened = Event()
socket_starting = Event()
socket_lock = Lock()


# --------------------------------------
# API and input helpers
# --------------------------------------

def is_api_error(result):
    """Return True when a response clearly indicates an API error."""
    return isinstance(result, dict) and str(result.get("stat", "")).lower() in {
        "not_ok",
        "error",
        "failed",
    }


def show_result(result):
    """Display an API response without hiding explicit API errors."""
    if result is None:
        print("API returned no data.")
        return

    if is_api_error(result):
        print("API error:", result.get("emsg") or result.get("message") or result)
        return

    print("Result:", result)


def api_call(method, **kwargs):
    """Call an API method and return None if it raises an exception."""
    try:
        return method(**kwargs)
    except Exception as exc:
        # Do not print request arguments: they may contain account details.
        logging.error("API request failed in %s (%s)", getattr(method, "__name__", "API method"), type(exc).__name__)
        print("Request failed. Check the API connection, session, and parameters.")
        return None


def get_text(prompt, *, required=True, default=None, uppercase=False):
    """Read text input, optionally using a default value."""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            raw = default
        if required and not raw:
            print("This field is required.")
            continue
        return raw.upper() if uppercase else raw


def get_number(prompt, integer=False, positive=True):
    """Read a finite number and validate its sign and integer constraint."""
    while True:
