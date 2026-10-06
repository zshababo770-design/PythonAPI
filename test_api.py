import os
import logging
from dotenv import load_dotenv

from api_helper import NorenApiPy


# Load variables from .env
load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def main():
    # Create API client
    api = NorenApiPy()

    # Read credentials from environment
    user_id = os.getenv("FLATTRADE_USER_ID")
    user_token = os.getenv("FLATTRADE_USER_TOKEN")

    if not user_id:
        raise ValueError("FLATTRADE_USER_ID is missing")

    if not user_token:
        raise ValueError("FLATTRADE_USER_TOKEN is missing")

    try:
        # Create API session
        logging.info("Creating Flattrade API session...")

        session = api.set_session(
            userid=user_id,
            password="",
            usertoken=user_token
        )

        print("\nSession response:")
        print(session)

        # Check session response
        if not session:
            raise RuntimeError("Empty response received from Flattrade API")

        if isinstance(session, dict):
            stat = session.get("stat")

            if stat != "Ok":
                raise RuntimeError(
                    f"Flattrade session failed: {session}"
                )

        print("\nSession created successfully.")

        # Get account limits
        logging.info("Fetching account limits...")

        limits = api.get_limits()

        print("\nAccount limits:")
        print(limits)

    except Exception as e:
        logging.exception("Flattrade API error: %s", e)


if __name__ == "__main__":
    main()
