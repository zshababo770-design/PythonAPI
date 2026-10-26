import logging
import os
import getpass
from datetime import datetime

# Assumes your existing project defines:
# - NorenApiPy-compatible self.api
# - IST timezone
# - ask(prompt, default=None)
# - show(value)
# - MarketApp.__init__(), on_order(), on_quote(), on_open(), on_close()
#
# Replace the corresponding methods in your MarketApp class with these.
# Keep your existing imports and __init__/callback implementations.

LOG = logging.getLogger(__name__)


def connect(self):
    """Create and verify an authenticated Flattrade API session."""
    user_id = (os.getenv("FLATTRADE_USER_ID") or ask("Flattrade user ID")).strip()
    token = (
        os.getenv("FLATTRADE_USER_TOKEN")
        or getpass.getpass("Session token: ")
    ).strip()

    if not user_id or not token:
        raise ValueError("A Flattrade user ID and session token are required.")
    if user_id == "YOUR_USER_ID" or token == "YOUR_USER_TOKEN":
        raise ValueError("Replace the placeholder credentials with real values.")

    try:
        response = self.api.set_session(userid=user_id, password="", usertoken=token)
    except Exception as exc:
        raise RuntimeError(f"Could not create API session: {exc}") from exc

    if isinstance(response, dict) and str(response.get("stat", "")).lower() in {
        "not_ok", "not ok", "error"
    }:
        raise RuntimeError(response.get("emsg") or "Session setup failed.")

    # A setter's return value may not prove the session works; verify it.
    try:
        validation = self.api.get_limits()
    except Exception as exc:
        raise RuntimeError(f"Session validation request failed: {exc}") from exc

    if not isinstance(validation, dict) or validation.get("stat") != "Ok":
        detail = (
            validation.get("emsg", "No successful response.")
            if isinstance(validation, dict)
            else "No valid response."
        )
        raise RuntimeError(f"Session validation failed: {detail}")

    self.session_created = True
    LOG.info("Flattrade API session verified.")


def start_socket(self):
    """Start the WebSocket once and subscribe after it opens."""
    if getattr(self, "socket_started", False):
        print("WebSocket is already started. Use x to stop it before restarting.")
        return

    raw = ask("Subscriptions (comma-separated EXCHANGE|TOKEN)", "NSE|11630")
    subscriptions = list(dict.fromkeys(
        item.strip() for item in raw.split(",") if item.strip()
    ))

    def valid_subscription(item):
        parts = item.split("|")
        return (
            len(parts) == 2
            and bool(parts[0].strip())
            and bool(parts[1].strip())
            and parts[0].strip().isalnum()
            and parts[1].strip().isdigit()
        )

    if not subscriptions or not all(valid_subscription(item) for item in subscriptions):
        raise ValueError("Use EXCHANGE|TOKEN format, e.g. NSE|11630,BSE|522032.")

    self.subscriptions = subscriptions
    self.socket_opened.clear()
    self.socket_started = True

    try:
        self.api.start_websocket(
            order_update_callback=self.on_order,
            subscribe_callback=self.on_quote,
            socket_open_callback=self.on_open,
            socket_close_callback=self.on_close,
        )
    except Exception:
        self.socket_started = False
