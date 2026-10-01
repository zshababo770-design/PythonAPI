from api_helper import NorenApiPy, get_time
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Flag to tell us if the websocket is open
socket_opened = False

# API object
api = NorenApiPy()


# -----------------------------
# WebSocket callbacks
# -----------------------------

def event_handler_order_update(message):
    print("Order event:", message)


def event_handler_quote_update(message):
    print("Quote event:", message)


def open_callback():
    global socket_opened

    socket_opened = True
    print("App is connected")

    # Subscribe to INFY
    api.subscribe("NSE|22")

    # Example:
    # api.subscribe(["NSE|22", "BSE|522032"])


# -----------------------------
# Main program
# -----------------------------

def main():

    # Flattrade login information
    user_session = "YOUR_USER_TOKEN"
    user_id = "YOUR_USER_ID"

    # Create API session
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
        print("p => place order")
        print("m => modify order")
        print("c => cancel order")
        print("y => order history")
        print("o => get order book")
        print("h => get holdings")
        print("l => get limits")
        print("k => get positions")
        print("d => get daily MTM")
        print("s => start websocket")
        print("q => quit")
        print("==============================")

        prompt1 = input("What shall we do? ").lower().strip()

        # -----------------------------
        # Place order
        # -----------------------------
        if prompt1 == "p":

            ret = api.place_order(
                buy_or_sell="B",
                product_type="C",
                exchange="NSE",
                tradingsymbol="INFY-EQ",
                quantity=1,
                discloseqty=0,
                price_type="LMT",
                price=1500.00,
                trigger_price=None,
                retention="DAY",
                remarks="my_order_001"
            )

            print(ret)

        # -----------------------------
        # Modify order
        # -----------------------------
        elif prompt1 == "m":

            orderno = input("Enter order number: ").strip()

            ret = api.modify_order(
                exchange="NSE",
                tradingsymbol="INFY-EQ",
                orderno=orderno,
                newquantity=2,
                newprice_type="LMT",
                newprice=1505.00
            )

            print(ret)

        # -----------------------------
        # Cancel order
        # -----------------------------
        elif prompt1 == "c":

            orderno = input("Enter order number: ").strip()

            ret = api.cancel_order(
                orderno=orderno
            )

            print(ret)

        # -----------------------------
        # Order history
        # -----------------------------
        elif prompt1 == "y":

            orderno = input("Enter order number: ").strip()

            ret = api.single_order_history(
                orderno=orderno
            )

            print(ret)

        # -----------------------------
        # Order book
        # -----------------------------
        elif prompt1 == "o":

            ret = api.get_order_book()

            print(ret)

        # -----------------------------
        # Holdings
        # -----------------------------
        elif prompt1 == "h":

            ret = api.get_holdings()

            print(ret)

        # -----------------------------
        # Limits
        # -----------------------------
        elif prompt1 == "l":

            ret = api.get_limits()

            print(ret)

        # -----------------------------
        # Positions
        # -----------------------------
        elif prompt1 == "k":

            ret = api.get_positions()

            print(ret)

        # -----------------------------
        # Daily MTM / P&L
        # -----------------------------
        elif prompt1 == "d":

            ret = api.get_positions()

            if not ret:
                print("No position data available.")
                continue

            mtm = 0.0
            pnl = 0.0

            for position in ret:
                try:
                    mtm += float(position.get("urmtom", 0))
                    pnl += float(position.get("rpnl", 0))
                except (ValueError, TypeError):
                    continue

            day_mtm = mtm + pnl

            print("\n------------------------------")
            print(f"Unrealized MTM : {mtm:.2f}")
            print(f"Realized P&L   : {pnl:.2f}")
            print(f"Day MTM / P&L  : {day_mtm:.2f}")
            print("------------------------------")

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

            try:
                ret = api.logout()
                print(ret)
            except Exception as e:
                print("Logout error:", e)

            print("Fin")
            break

        # -----------------------------
        # Invalid option
        # -----------------------------
        else:

            print(
                "Invalid option. "
                "Please choose p, m, c, y, o, h, l, k, d, s, or q."
            )


# Only run when this file is executed directly
if __name__ == "__main__":
    main()
