from api_helper import NorenApiPy
import logging

# Enable debug logging to see requests and responses
logging.basicConfig(level=logging.DEBUG)


def main():
    # Start API
    api = NorenApiPy()

    # Replace these with your actual Flattrade credentials
    user_id = "YOUR_USER_ID"
    user_session = "YOUR_USER_TOKEN"

    # Create API session
    ret = api.set_session(
        userid=user_id,
        password="",
        usertoken=user_session
    )

    print("Session response:")
    print(ret)

    # Get account limits
    ret = api.get_limits()

    print("Account limits:")
    print(ret)


if __name__ == "__main__":
    main()
