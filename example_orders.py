
import os
import logging
from decimal import Decimal, InvalidOperation
from threading import Event, Lock

from api_helper import NorenApiPy


# --------------------------------------
# Configuration
# --------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

USER_ID = os.getenv("FLATTRADE_USER_ID", "").strip()
USER_TOKEN = os.getenv("FLATTRADE_USER_TOKEN", "").strip()

api = NorenApiPy()

socket_opened = Event()
socket_lock = Lock()


# --------------------------------------
# Helper functions
# --------------------------------------

def show_result(result):
    if result is None:
        print("API returned no data.")
        return

    if isinstance(result, dict):
        if result.get("stat") == "Not_Ok":
            print("API error:", result.get("emsg", result))
            return

    print("Result:", result)


def api_call(method, **kwargs):
    try:
        return method(**kwargs)
    except Exception as exc:
        logging.error(
            "API request failed: %s",
            type(exc).__name__
        )
        print("Request failed. Check API connection or parameters.")
        return None


def get_number(prompt, integer=False, positive=True):
    while True:
        raw = input(prompt).strip()

        try:
            value = Decimal(raw)

            if not value.is_finite():
                raise ValueError

            if positive and value <= 0:
                print("Please enter a positive number.")
                continue

            if not positive and value < 0:
                print("Value cannot be negative.")
                continue

            if integer:
                if value != value.to_integral_value():
                    print("Please enter a whole number.")
                    continue
                return int(value)

            return float(value)

        except (InvalidOperation, ValueError):
            print("Invalid number. Try again.")


def confirm_action(description):
    print("\n" + description)
    answer = input("Confirm? Type YES: ").strip()
    return answer == "YES"


def get_valid_positions():
    result = api_call(api.get_positions)

    if isinstance(result, list):
        return result

    show_result(result)
    return []


def get_order_details(order_number):
    result = api_call(api.single_order_history, orderno=order_number)

    if isinstance(result, list) and result:
        return result[-1]

    if isinstance(result, dict) and result.get("stat") == "Ok":
        return result

    return None


# --------------------------------------
# WebSocket callbacks
# --------------------------------------

def event_handler_order_update(message):
    print("\n[ORDER UPDATE]", message)


def event_handler_quote_update(message):
    if not isinstance(message, dict):
        print("\n[QUOTE]", message)
        return

    print(
        "\n[QUOTE]",
        "Token:", message.get("tk"),
        "LTP:", message.get("lp", "N/A"),
        "Change:", message.get("pc", "N/A")
    )


def open_callback():
    with socket_lock:
        socket_opened.set()

    print("\nWebSocket connected.")

    try:
        api.subscribe("NSE|22")
        print("Subscribed to NSE|22 (INFY).")
    except Exception as exc:
        logging.warning(
            "Subscription failed: %s",
            type(exc).__name__
        )


def close_callback(*args):
    with socket_lock:
        socket_opened.clear()

    print("\nWebSocket disconnected.")


def start_socket():
    if socket_opened.is_set():
        print("WebSocket is already connected.")
        return

    print("Starting WebSocket...")

    result = api_call(
        api.start_websocket,
        order_update_callback=event_handler_order_update,
        subscribe_callback=event_handler_quote_update,
        socket_open_callback=open_callback,
        socket_close_callback=close_callback
    )

    if result is not None:
        show_result(result)

    print("Connection is asynchronous. Check connection messages.")


# --------------------------------------
# Order management
# --------------------------------------

def place_order():
    print("\n--- Place Order ---")

    exchange = input("Exchange [NSE]: ").strip().upper() or "NSE"
    symbol = input("Trading symbol [INFY-EQ]: ").strip().upper() or "INFY-EQ"

    side = input("Buy (B) or Sell (S): ").strip().upper()

    if side not in ("B", "S"):
        print("Invalid order side.")
        return

    product = input("Product type [C]: ").strip().upper() or "C"
    quantity = get_number("Quantity: ", integer=True)

    price_type = input("Price type (LMT/MKT): ").strip().upper()

    if price_type not in ("LMT", "MKT"):
        print("Unsupported price type.")
        return

    price = (
        get_number("Limit price: ")
        if price_type == "LMT"
        else 0.0
    )

    description = (
        f"{side} {quantity} {symbol} on {exchange}\n"
        f"Product: {product}\n"
        f"Order type: {price_type}\n"
        f"Price: {price}"
    )

    if not confirm_action(description):
        print("Order cancelled locally.")
        return

    result = api_call(
        api.place_order,
        buy_or_sell=side,
        product_type=product,
        exchange=exchange,
        tradingsymbol=symbol,
        quantity=quantity,
        discloseqty=0,
        price_type=price_type,
        price=price,
        trigger_price=None,
        retention="DAY",
        remarks="python_cli"
    )

    show_result(result)


def modify_order():
    print("\n--- Modify Order ---")

    order_number = input("Order number: ").strip()

    if not order_number:
        print("Order number is required.")
        return

    details = get_order_details(order_number)

    if not details:
        print("Could not verify order details. Modification stopped.")
        return

    exchange = details.get("exch")
    symbol = details.get("tsym")

    if not exchange or not symbol:
        print("Order exchange or symbol missing.")
        return

    print("Order:", order_number)
    print("Symbol:", symbol)
    print("Exchange:", exchange)

    quantity = get_number("New quantity: ", integer=True)
    price_type = input("New price type (LMT/MKT): ").strip().upper()

    if price_type not in ("LMT", "MKT"):
        print("Invalid price type.")
        return

    price = (
        get_number("New limit price: ")
        if price_type == "LMT"
        else 0.0
    )

    if not confirm_action(
        f"Modify {order_number}: {quantity} units at {price_type} {price}"
    ):
        return

    result = api_call(
        api.modify_order,
        exchange=exchange,
        tradingsymbol=symbol,
        orderno=order_number,
        newquantity=quantity,
        newprice_type=price_type,
        newprice=price
    )

    show_result(result)


def cancel_order():
    print("\n--- Cancel Order ---")

    order_number = input("Order number: ").strip()

    if not order_number:
        print("Order number is required.")
        return

    if not confirm_action(f"Cancel order {order_number}?"):
        return

    result = api_call(
        api.cancel_order,
        orderno=order_number
    )

    show_result(result)


def order_history():
    order_number = input("Order number: ").strip()

    if not order_number:
        print("Order number is required.")
        return

    result = api_call(
        api.single_order_history,
        orderno=order_number
    )

    show_result(result)


# --------------------------------------
# Portfolio and P&L
# --------------------------------------

def daily_mtm():
    positions = get_valid_positions()

    if not positions:
        print("No positions available.")
        return

    unrealized = Decimal("0")
    realized = Decimal("0")

    for position in positions:
        if not isinstance(position, dict):
            continue

        try:
            unrealized += Decimal(
                str(position.get("urmtom") or 0)
            )
            realized += Decimal(
                str(position.get("rpnl") or 0)
            )
        except (InvalidOperation, ValueError, TypeError):
            print("Warning: skipped invalid P&L values.")
            continue

    total = unrealized + realized

    print("\n--------------------------------")
    print(f"Unrealized MTM : {unrealized:,.2f}")
    print(f"Realized P&L   : {realized:,.2f}")
    print(f"Total MTM/P&L  : {total:,.2f}")
    print("--------------------------------")


# --------------------------------------
# Login / Session
# --------------------------------------

def create_session():
    if not USER_ID or not USER_TOKEN:
        print(
            "Missing credentials.\n"
            "Set FLATTRADE_USER_ID and FLATTRADE_USER_TOKEN."
        )
        return False

    result = api_call(
        api.set_session,
        userid=USER_ID,
        password="",
        usertoken=USER_TOKEN
    )

    if result is None or result is False:
        print("Failed to configure API session.")
        return False

    # set_session configures a token; a protected API request
    # is used to test whether the token is accepted.
    limits = api_call(api.get_limits)

    if (
        not isinstance(limits, dict)
        or limits.get("stat") != "Ok"
    ):
        print("Session validation failed.")
        show_result(limits)
        return False

    print("API session verified successfully.")
    return True


# --------------------------------------
# Main menu
# --------------------------------------

def show_menu():
    print("""
====================================
        FLATTRADE TRADING CLI
====================================
 p  => Place Order
 m  => Modify Order
 c  => Cancel Order
 y  => Order History
 o  => Order Book
 h  => Holdings
 l  => Limits
 k  => Positions
 d  => Daily MTM / P&L
 s  => Start WebSocket
 q  => Quit
====================================
""")


def main():
    if not create_session():
        return

    try:
        while True:
            show_menu()

            choice = input("Choose an option: ").strip().lower()

            if choice == "p":
                place_order()

            elif choice == "m":
                modify_order()

            elif choice == "c":
                cancel_order()

            elif choice == "y":
                order_history()

            elif choice == "o":
                show_result(api_call(api.get_order_book))

            elif choice == "h":
                show_result(api_call(api.get_holdings))

            elif choice == "l":
                show_result(api_call(api.get_limits))

            elif choice == "k":
                show_result(api_call(api.get_positions))

            elif choice == "d":
                daily_mtm()

            elif choice == "s":
                start_socket()

            elif choice == "q":
                print("Closing application...")
                break

            else:
                print("Invalid option. Please try again.")

    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted by user.")

    finally:
        try:
            api.logout()
            print("Logged out.")
        except Exception:
            print("Logout could not be confirmed.")

        print("Application closed.")


if __name__ == "__main__":
    main()
