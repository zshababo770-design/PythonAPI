import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from NorenRestApiPy.NorenApi import NorenApi


logger = logging.getLogger(__name__)


@dataclass
class Order:
    buy_or_sell: Optional[str] = None
    product_type: Optional[str] = None
    exchange: Optional[str] = None
    tradingsymbol: Optional[str] = None
    price_type: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    discloseqty: int = 0
    retention: str = "DAY"
    remarks: str = "tag"
    order_id: Optional[str] = None

    def validate(self) -> None:
        for field in (
            "buy_or_sell",
            "product_type",
            "exchange",
            "tradingsymbol",
            "price_type",
            "retention",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")

        if self.buy_or_sell not in {"B", "S"}:
            raise ValueError("buy_or_sell must be 'B' or 'S'")

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise ValueError("quantity must be a positive integer")

        if (
            isinstance(self.discloseqty, bool)
            or not isinstance(self.discloseqty, int)
            or not 0 <= self.discloseqty <= self.quantity
        ):
            raise ValueError(
                "discloseqty must be an integer between 0 and quantity"
            )


def get_time(time_string: str) -> float:
    """Convert DD-MM-YYYY HH:MM:SS using the machine's local timezone."""
    return time.mktime(
        time.strptime(time_string, "%d-%m-%Y %H:%M:%S")
    )


class NorenApiPy(NorenApi):
    def __init__(self):
        super().__init__(
            host="https://piconnect.flattrade.in/PiConnectAPI/",
            websocket="wss://piconnect.flattrade.in/PiConnectWSAPI/",
        )

    def placeOrder(self, order: Order):
        """Submit once and return the SDK's original response."""
        if not isinstance(order, Order):
            raise TypeError("order must be an Order instance")

        order.validate()

        return super().place_order(
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

    def _submit_order(self, index: int, order: Order) -> dict:
        result = {
            "index": index,
            "tradingsymbol": order.tradingsymbol,
            "status": "unknown",
            "response": None,
            "error": None,
        }

        try:
            response = self.placeOrder(order)
            result["response"] = response

            if isinstance(response, dict):
                if response.get("stat") == "Ok":
                    result["status"] = "accepted"
                elif response.get("stat") == "Not_Ok":
                    result["status"] = "rejected"
                    result["error"] = (
                        response.get("emsg") or "API rejected the order"
                    )

            if result["status"] == "unknown":
                result["error"] = (
                    "Unexpected response. Check the order book "
                    "before submitting this order again."
                )

        except Exception as exc:
            # An exception does not prove the broker rejected the order.
            # Avoid logging raw exception text, which may contain secrets.
            result["error"] = (
                f"{type(exc).__name__} during submission. "
                "Check the order book before submitting this order again."
            )
            logger.warning(
                "Submission outcome unknown for basket index %d (%s)",
                index,
                type(exc).__name__,
            )

        return result

    def place_basket(self, orders, max_workers: int = 1) -> list:
        """
        Return one structured result per order, in input order.

        Validate the entire basket before submitting any order.
        This is not an atomic transaction: some orders may be accepted
        while others are rejected or have an unknown outcome.
        """
        if (
            isinstance(max_workers, bool)
            or not isinstance(max_workers, int)
            or not 1 <= max_workers <= 10
        ):
            raise ValueError("max_workers must be an integer from 1 to 10")

        orders = list(orders)

        if not orders:
            return []

        for index, order in enumerate(orders):
            if not isinstance(order, Order):
                raise TypeError(f"Order at index {index} is not an Order")

            try:
                order.validate()
            except ValueError as exc:
                raise ValueError(
                    f"Invalid order at index {index}: {exc}"
                ) from exc

        results = [None] * len(orders)

        if max_workers == 1:
            for index, order in enumerate(orders):
                results[index] = self._submit_order(index, order)
        else:
            with ThreadPoolExecutor(
                max_workers=min(max_workers, len(orders))
            ) as executor:
                futures = {
                    executor.submit(self._submit_order, index, order): index
                    for index, order in enumerate(orders)
                }

                for future in as_completed(futures):
                    index = futures[future]
                    results[index] = future.result()

        counts = {
            status: sum(item["status"] == status for item in results)
            for status in ("accepted", "rejected", "unknown")
        }

        logger.info(
            "Basket completed: %d accepted, %d rejected, %d unknown",
            counts["accepted"],
            counts["rejected"],
            counts["unknown"],
        )

        return results
