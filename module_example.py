from xmrto_wrapper import xmrto_wrapper
import logging
import time


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper").setLevel(logging.INFO)

if __name__ == "__main__":
    order = xmrto_wrapper.create_order(
        out_address="3P8uJYvU4WZxu3dnXar7bGdePvbBSVKc5Q", btc_amount=0.01
    )
    print("=== Order created.")
    print(f"Order: {order}")
    print("=== Get order status by uuid.")
    order_status = xmrto_wrapper.track_order(uuid=order.uuid)
    print(f"Order status: {order_status}")
    print("=== Get order status by order_status object.")
    order_status.get_order_status()
    print(f"Order status: {order_status}")
    print("=== Get order status by order object.")
    print("Waiting 3 seconds to let XMR.to process the order.")
    time.sleep(3)
    order.get_order_status()
    print(f"Order: {order}")
    print(f"Subaddress to pay: {order.payment_subaddress}")
