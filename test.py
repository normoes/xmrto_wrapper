import xmrto_wrapper
import logging


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper").setLevel(logging.DEBUG)

if __name__ == "__main__":
    order = xmrto_wrapper.create_order(
        out_address="3P8uJYvU4WZxu3dnXar7bGdePvbBSVKc5Q", btc_amount=0.01
    )
    print("===")
    print(f"order: {order}")
    print("===")
    order.get_order_status()
    print(f"order subaddress to pay: {order.payment_subaddress}")
    print("===")
    status = xmrto_wrapper.track_order(uuid=order.uuid)
    print(f"order status: {status}")
