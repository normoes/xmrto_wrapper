from xmrto_wrapper import xmrto_wrapper
import logging


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper").setLevel(logging.INFO)

if __name__ == "__main__":
    order = xmrto_wrapper.create_order(
        out_address="3P8uJYvU4WZxu3dnXar7bGdePvbBSVKc5Q", btc_amount=0.01
    )
    print("=== Order created.")
    print(f"order: {order}")
    print("=== Get order status by uuid.")
    order_status = xmrto_wrapper.track_order(uuid=order.uuid)
    print(f"order status: {order_status}")
    print("=== Get order status by order_status object.")
    order_status.get_order_status()
    print(f"order status: {order_status}")
    print("=== Get order status by order object.")
    order.get_order_status()
    print(f"order subaddress to pay: {order.payment_subaddress}")
