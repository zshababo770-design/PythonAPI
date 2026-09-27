```python
import os
import sys
import logging
import timeit

# Add the parent directory to the Python path
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from api_helper import NorenApiPy, Order

# Enable debug logging
logging.basicConfig(level=logging.INFO)

# Initialize API client
client = NorenApiPy()

# Authentication placeholders
# Replace these values with valid credentials before actual use.
session_token = "YOUR_SESSION_TOKEN"
account_id = "YOUR_USER_ID"

# Create API session
session = client.set_session(
    userid=account_id,
    password="",
    usertoken=session_token
)

# Prepare sample basket orders
basket_orders = []

for quantity in range(1, 5):
    trade = Order()

    trade.buy_or_sell = "B"
    trade.product_type = "C"
    trade.exchange = "NSE"
    trade.tradingsymbol = "INFY-EQ"

    trade.quantity = quantity
    trade.discloseqty = 0

    trade.price_type = "LMT"
    trade.price = 1500.00
    trade.trigger_price = None

    trade.retention = "DAY"
    trade.remarks = "sample_basket_order"

    basket_orders.append(trade)

# Measure API execution time
start = timeit.default
```
