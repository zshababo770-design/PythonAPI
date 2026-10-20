import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from api_helper import NorenApiPy


logger = logging.getLogger(__name__)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def redact(text: str, token: str) -> str:
    """Remove the session token from application output."""
    return text.replace(token, "[REDACTED]") if token else text


def configure_session(api, user_id: str, token: str) -> None:
    result = api.set_session(
        userid=user_id,
        password="",
        usertoken=token,
    )

    # Some SDK versions return None on successful configuration.
    # The account-limits request below verifies authentication.
    if result is False:
        raise RuntimeError("The SDK could not configure the session")

    if isinstance(result, dict) and result.get("stat") == "Not_Ok":
        raise RuntimeError(
            result.get("emsg") or "Session configuration failed"
        )


def fetch_limits(api) -> dict:
    limits = api.get_limits()

    if not isinstance(limits, dict):
        raise RuntimeError(
            "No valid account-limits response received. "
            "Check your connection, user ID, and session token."
        )

    if limits.get("stat") != "Ok":
        raise RuntimeError(
            limits.get("emsg") or "Account-limits request failed"
        )

    return limits


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    token = ""

    try:
        # Existing environment variables take priority over .env.
        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path, override=False)

        user_id = require_env("FLATTRADE_USER_ID")
        token = require_env("FLATTRADE_USER_TOKEN")

        api = NorenApiPy()

        logger.info("Configuring Flattrade API session...")
        configure_session(api, user_id, token)

        logger.info("Verifying session and fetching account limits...")
        limits = fetch_limits(api)

        # Redact before JSON encoding to handle escaped characters.
        safe_limits = json.loads(
            json.dumps(limits),
            parse_int=int,
        )
        output = json.dumps(safe_limits, indent=2, ensure_ascii=False)
        output = redact(output, token)

        logger.info("Session verified successfully.")
        print(f"\nAccount limits:\n{output}")
        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled.")
        return 130

    except Exception as exc:
        logger.error(
            "%s: %s",
            type(exc).__name__,
            redact(str(exc), token),
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
