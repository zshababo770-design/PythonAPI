from api_helper import NorenApiPy, get_time
import logging
import time
import pandas as pd

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Flag to tell us if the websocket is open
socket_opened = False


# -----------------------------
# WebSocket callbacks
# -----------------------------

def event_handler_order_update(message):
    print("Order event:", message)


def event_handler_quote_update(message):
    print(
        "Quote event: "
        + time.strftime("%d-%m-%Y %H:%M:%S")
        + " "
        + str(message)
    )


def open_callback():
    global socket_opened

    socket_opened = True
    print("App is connected")

    # Subscribe to NSE token 11630
    api.subscribe("NSE|11630")

    # Example:
    # api.subscribe(["NSE|22", "BSE|522032"])


# -----------------------------
# Main program
# -----------------------------

def main():

    # Start API
    api = NorenApiPy()

    # Your Flattrade login information
    user_session = "YOUR_USER_TOKEN"
    user_id = "YOUR_USER_ID"

    # Create session
    ret = api.set_session(
        userid=user_id,
        password="",
        usertoken=user_session
    )

    if ret is None:
        print("Failed to create API session.")
        return

    print("API session created successfully.")

    while True:

        print("\n==============================")
        print("f => find symbol")
        print("m => get quotes")
        print("p => contract info / properties")
        print("v => get 1 min market data")
        print("t => get today's 1 min market data")
        print("d => get daily data")
        print("o => get option chain")
        print("s => start websocket")
        print("q => quit")
        print("==============================")

        prompt1 = input("What shall we do? ").lower().strip()

        # -----------------------------
        # 1-minute historical data
        # -----------------------------
        if prompt1 == "v":

            start_time = "13-07-2021 09:10:00"
            end_time = "13-07-2021 09:20:00"

            start_secs = get_time(start_time)
            end_secs = get_time(end_time)

            ret = api.get_time_price_series(
                exchange="NSE",
                token="22",
                starttime=start_secs,
                endtime=end_secs
            )

            if ret:
                df = pd.DataFrame.from_dict(ret)
                print(df)
            else:
                print("No market data returned.")

            print(f"{start_secs} to {end_secs}")

        # -----------------------------
        # Today's 1-minute data
        # -----------------------------
        elif prompt1 == "t":

            ret = api.get_time_price_series(
                exchange="NSE",
                token="22"
            )

            if ret:
                df = pd.DataFrame.from_dict(ret)
                print(df)
            else:
                print("No market data returned.")

        # -----------------------------
        # Find symbol
        # -----------------------------
        elif prompt1 == "f":

            exchange = "NFO"
            query = "BANKNIFTY 30DEC CE"

            ret = api.searchscrip(
                exchange=exchange,
                searchtext=query
            )

            print(ret)

            if ret and "values" in ret:

                symbols = ret["values"]

                for symbol in symbols:
                    print(
                        f"{symbol['tsym']} token is {symbol['token']}"
                    )

        # -----------------------------
        # Daily data
        # -----------------------------
        elif prompt1 == "d":

            exchange = "NSE"
            trading_symbol = "RELIANCE-EQ"

            ret = api.get_daily_price_series(
                exchange=exchange,
                tradingsymbol=trading_symbol,
                startdate=0
            )

            print(ret)

        # -----------------------------
        # Security information
        # -----------------------------
        elif prompt1 == "p":

            exchange = "NSE"
            token = "22"

            ret = api.get_security_info(
                exchange=exchange,
                token=token
            )

            print(ret)

        # -----------------------------
        # Current quote
        # -----------------------------
        elif prompt1 == "m":

            exchange = "NSE"
            token = "22"

            ret = api.get_quotes(
                exchange=exchange,
                token=token
            )

            print(ret)

        # -----------------------------
        # Option chain
        # -----------------------------
        elif prompt1 == "o":

            exchange = "NFO"
            trading_symbol = "COFORGE30DEC21F"

            chain = api.get_option_chain(
                exchange=exchange,
                tradingsymbol=trading_symbol,
                strikeprice=3500,
                count=2
            )

            if chain and "values" in chain:

                chain_scrips = []

                for scrip in chain["values"]:

                    scrip_data = api.get_quotes(
                        exchange=scrip["exch"],
                        token=scrip["token"]
                    )

                    chain_scrips.append(scrip_data)

                print(chain_scrips)

            else:
                print("No option chain data returned.")

        # -----------------------------
        # Start WebSocket
        # -----------------------------
        elif prompt1 == "s":

            if socket_opened:
                print("WebSocket already opened.")
                continue

            ret = api.start_websocket(
                order_update_callback=event_handler_order_update,
                subscribe_callback=event_handler_quote_update,
                socket_open_callback=open_callback
            )

            print(ret)

        # -----------------------------
        # Quit
        # -----------------------------
        elif prompt1 == "q":

            ret = api.logout()
            print(ret)

            print("Fin")
            break

        else:
            print("Invalid option. Please choose f, m, p, v, t, d, o, s, or q.")


# Only run when this file is executed directly
if __name__ == "__main__":
    main()
