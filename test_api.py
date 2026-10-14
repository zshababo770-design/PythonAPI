import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from api_helper import NorenApiPy


# Load .env from the script's directory.
# Existing environment variables take priority.
load_dotenv(Path(__file__).resolve().parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def require_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing or empty")
    return value


def main():
    user_token = ""

    try:
        user_id = require_env("FLATTRADE_USER_ID")
        user_token = require_env("FLATTRADE_USER_TOKEN")

        api = NorenApiPy()

        logger.info("Configuring Flattrade API session...")

        session = api.set_session(
            userid=user_id,
            password="",
            usertoken=user_token,
        )

        # Reject explicit failures without assuming a particular
        # success return format across SDK versions.
        if session is False:
            raise RuntimeError("The SDK could not configure the session")

        if isinstance(session, dict) and session.get("stat") == "Not_Ok":
            raise RuntimeError(
                session.get("emsg") or "Session configuration failed"
            )

        logger.info("Verifying session and fetching account limits...")
        limits = api.get_limits()

        if not isinstance(limits, dict):
            raise RuntimeError(
                "No valid account-limits response received. "
                "Check your connection, user ID, and session token."
            )

        if limits.get("stat") != "Ok":
            raise RuntimeError(
                limits.get("emsg")
                or "Account-limits request failed"
            )

        logger.info("Session verified successfully.")

        print("\nAccount limits:")
        print(json.dumps(limits, indent=2, ensure_ascii=False))
        return 0

    except Exception as exc:
        # Avoid exposing the session token in error messages.
        message = str(exc)
        if user_token:
            message = message.replace(user_token, "[REDACTED]")

        logger.error("%s: %s", type(exc).__name__, message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
