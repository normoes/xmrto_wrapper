import xmrto_wrapper
import logging


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper").setLevel(logging.DEBUG)

if __name__ == "__main__":
    order = xmrto_wrapper.create_order(
        out_address="3P8uJYvU4WZxu3dnXar7bGdePvbBSVKc5Q", out_amount=0.01
    )
    print(order)
    status = xmrto_wrapper.track_order(uuid=order.uuid)
    print(status)
