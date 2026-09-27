from NorenRestApiPy.NorenApi import NorenApi
from threading import Timer
import pandas as pd
import time
import concurrent.futures

api = None


class Order:
    def __init__(
        self,
        buy_or_sell: str = None,
        product_type: str = None,
        exchange: str = None,
        tradingsymbol: str = None,
        price_type: str = None,
        quantity: int = None,
        price: float = None,
        trigger_price: float = None,
        discloseqty: int = 0,
        retention: str = "DAY",
        remarks: str = "tag",
        order_id: str = None,
    ):
        self.buy_or_sell = buy_or_sell
        self.product_type = product_type
        self.exchange = exchange
        self.tradingsymbol = tradingsymbol
        self.quantity = quantity
        self.discloseqty = discloseqty
        self.price_type = price_type
        self.price = price
        self.trigger_price = trigger_price
        self.retention = retention
        self.remarks = remarks
        self.order_id = order_id


def get_time(time_string):
    data = time.strptime(time_string, "%d-%m-%Y %H:%M:%S")
    return time.mktime(data)


class NorenApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(
            self,
            host="https://piconnect.flattrade.in/PiConnectAPI/",
            websocket="wss://piconnect.flattrade.in/PiConnectWSAPI/",
        )

        global api
        api = self

    def place_basket(self, orders):
        result = []
        resp_ok = 0
        resp_err = 0

        if not orders:
            return result

        max_workers = min(10, len(orders))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            future_to_order = {
                executor.submit(self.placeOrder, order): order
                for order in orders
            }

            for future in concurrent.futures.as_completed(future_to_order):
                order = future_to_order[future]

                try:
                    response = future.result()
                    result.append(response)
                    resp_ok += 1

                except Exception as exc:
                    resp_err += 1

                    print(
                        f"Order failed: "
                        f"{order.tradingsymbol} - {exc}"
                    )

        print(
            f"Basket completed: "
            f"{resp_ok} successful, {resp_err} failed"
        )

        return result

    def placeOrder(self, order: Order):
        return NorenApi.place_order(
            self,
            buy_or_sell=order.buy_or_sell,
            product_type=order.product_type,
            exchange=order.exchange,
            tradingsymbol=order.tradingsymbol,
            quantity=order.quantity,
            discloseqty=order.discloseqty,
            price_type=order.price_type,
            price=order.price,
            trigger_price=order.trigger_price,
            retention=order.retention,
            remarks=order.remarks,
        )
