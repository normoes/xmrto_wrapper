#!/usr/bin/env python

"""
Goal:
  * Interact with XMR.to.

How to:
  * General usage
    - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
    - `python xmrto_wrapper.py track-order --secret-key xmrto-ebmA9q`
    - `python xmrto_wrapper.py create-and-track-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
    - `python xmrto_wrapper.py price --btc-amount 0.01`
    - `python xmrto_wrapper.py qrcode --data "something"`
  * Get help
    - xmrto_wrapper.py -h
  * You can
    - Create an order: `xmrto_wrapper.py create-order`
    - Track an order: `xmrto_wrapper.py track-order`
    - Get a recent price: `xmrto_wrapper.py price`
    - Create a QR code: `xmrto_wrapper.py qrcode`
  * The API used is `--api v2` by default, so no need to actually set that parameter.
  * The URL used is `--url https://xmr.to` by default, so no need to actually set that parameter.

When called as python script python `xmrto_wrapper.py` configure it using cli options.
When importing as module `import xmrto_wrapper` environment variables are considered.
"""

import os
import sys
import argparse
import logging
import json
import time
import collections
from typing import Dict

from requests import auth, Session, codes
from requests.exceptions import ConnectionError, SSLError


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper")
logger.setLevel(logging.INFO)


XMRTO_URL_DEFAULT = "https://xmr.to"
API_VERSION_DEFAULT = "v2"

XMRTO_URL = os.environ.get("XMRTO_URL", XMRTO_URL_DEFAULT)
API_VERSION = os.environ.get("API_VERSION", API_VERSION_DEFAULT)
DESTINATION_ADDRESS = os.environ.get("BTC_ADDRESS", None)
BTC_AMOUNT = os.environ.get("BTC_AMOUNT", None)
XMR_AMOUNT = os.environ.get("XMR_AMOUNT", None)
CERTIFICATE = os.environ.get("XMRTO_CERTIFICATE", None)
QR_DATA = os.environ.get("QR_DATA", None)
SECRET_KEY = os.environ.get("SECRET_KEY", None)

# class Status():
#     def __init__(self, **fields):
#         self.state = fields["state"]
#         self.in_out_rate = fields["in_out_rate"]
#         self.payment_subaddress = fields.get("payment_subaddress", None)
#         self.payment_address = fields["payment_address"]
#         self.payment_integrated_address = fields.get("payment_integrated_address", None)
#         self.payment_id_long = fields.get("payment_id_long", None)
#         self.payment_id_short = fields.get("payment_id_short", None)
#         self.in_amount = fields["in_amount"]
#         self.in_amount_remaining = fields["in_amount_remaining"]
#         self.in_confirmations_remaining = fields["in_confirmations_remaining"]
#
#     def __str__(self):
#         return str(type(self)) + ": "  + json.dumps(self.__dict__)

STATUS_FIELDS = [
    "state",
    "in_out_rate",
    "btc_amount",
    "btc_amount_partial",
    "payment_subaddress",
    "payment_address",
    "payment_integrated_address",
    "payment_id_long",
    "payment_id_short",
    "in_amount",
    "in_amount_remaining",
    "in_confirmations_remaining",
    "seconds_till_timeout",
    "created_at",
]
Status = collections.namedtuple("Status", STATUS_FIELDS)
StatusClass = Status
ORDER_FIELDS = ("uuid", "state", "out_amount")
Order = collections.namedtuple("Order", ORDER_FIELDS)
PRICE_FIELDS = ("out_amount", "in_amount", "in_out_rate")
Price = collections.namedtuple("Price", PRICE_FIELDS)


class XmrtoConnection:
    USER_AGENT = "XmrtoProxy/0.1"
    HTTP_TIMEOUT = 30

    __conn = None

    def __init__(self, timeout: int = HTTP_TIMEOUT):
        self.__timeout = timeout
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
            # look at python-monerorpc to get TLD from URL
            # "Host": "xmr.to",
        }
        if not self.__conn:
            self.__conn = Session()
            self.__conn.headers = headers

    def get(self, url: str, expect_json=True):
        return self._request(url=url, func=self._get, expect_json=expect_json)

    def _get(self, url: str):
        return self.__conn.get(url=url, timeout=self.__timeout)

    def post(self, url: str, postdata: Dict[str, str], expect_json=True):
        return self._request(
            url=url, func=self._post, postdata=postdata, expect_json=expect_json
        )

    def _post(self, url: str, postdata: str, **kwargs):
        logger.debug(postdata)
        logger.debug(f"Additional request arguments: {kwargs}")
        return self.__conn.post(
            url=url, data=postdata, timeout=self.__timeout, **kwargs
        )

    def _request(
        self, url: str, func, postdata: Dict[str, str] = None, expect_json=True
    ):
        """Makes the HTTP request

        """

        logger.debug(f"--> URL: {url}")

        response = None
        try:
            try:
                data = dict({"url": url})
                if postdata:
                    data["postdata"] = json.dumps(postdata)

                response = func(**data)
            except (SSLError) as e:
                # Disable verification: verify=False
                # , cert=path_to_certificate
                # , verify=True
                logger.debug(
                    f"SSL certificate error, trying certificate: {CERTIFICATE}"
                )
                data["cert"] = CERTIFICATE
                data["verify"] = True

                response = func(**data)
        except (ConnectionError) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            error_msg["error_code"] = 102
            print(json.dumps(error_msg))
            return None
        except (Exception) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            error_msg["error_code"] = 103
            print(json.dumps(error_msg))
            return None

        response_ = None
        try:
            response_ = self._get_response(response=response, expect_json=expect_json)
        except (ValueError) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            error_msg["error_code"] = 100
            print(json.dumps(error_msg))
            return None

        if not response_:
            error_msg = dict({"error": "Could not evaluate response."})
            error_msg["url"] = url
            error_msg["error_code"] = 101
            print(json.dumps(error_msg))
            return None
        elif isinstance(response_, dict) and (not response_.get("error", None) is None):
            error_msg = response_
            error_msg["url"] = url
            # print(json.dumps(error_msg))
            return error_msg

        return response_

    def _get_response(self, response, expect_json=True):
        """Evaluate HTTP request response

        :return: Either JSON response or response object in case of PNG (QRCode)
        """

        # Compare against None
        # Response with 400 status code returns True for not response
        if response == None:
            raise ValueError(
                {"error": "No response.", "message": f"Response is {response}."}
            )

        if response.status_code not in [
            codes.ok,
            codes.created,
            codes.bad,
            codes.forbidden,
            codes.not_found,
        ]:
            raise ValueError(
                {
                    "error": "HTTP status code.",
                    "message": "Received HTTP status code {}".format(
                        response.status_code
                    ),
                }
            )
        http_response = response.text
        if http_response is None:
            raise ValueError(
                {
                    "error": "Empty response.",
                    "message": "Missing HTTP response from server",
                }
            )

        json_response = None
        try:
            json_response = json.loads(http_response)
        except (json.decoder.JSONDecodeError) as e:
            if expect_json:
                raise ValueError(
                    {
                        "error": "Expected JSON, got something else.",
                        "message": f"'{http_response}' with exception '{str(e)}'",
                    }
                )
            else:
                return response

        logger.debug(f"<-- {json_response}")

        return json_response


class CreateOrder:
    V1Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    V2Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    V3Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    apis = {"v1": V1Order, "v2": V2Order, "v3": V3Order}

    @classmethod
    def get(cls, data, api):
        order = cls.apis[api]
        if not order or not data:
            return None, None

        xmrto_error = None
        if "error" in data:
            xmrto_error = data

        uuid = data.get(order.uuid, None)
        state = data.get(order.state, None)
        out_amount = data.get(order.out_amount, None)

        return Order(uuid=uuid, state=state, out_amount=out_amount), xmrto_error


class OrderStatus:
    V1Status = StatusClass(
        state="state",
        in_out_rate="xmr_price_btc",
        btc_amount="btc_amount",
        btc_amount_partial="",
        payment_subaddress="xmr_receiving_subaddress",
        payment_address="xmr_receiving_address",
        payment_integrated_address="",
        payment_id_long="xmr_required_payment_id",
        payment_id_short="",
        in_amount="xmr_amount_total",
        in_amount_remaining="xmr_amount_remaining",
        in_confirmations_remaining="xmr_num_confirmations_remaining",
        seconds_till_timeout="seconds_till_timeout",
        created_at="created_at",
    )
    V2Status = StatusClass(
        state="state",
        in_out_rate="xmr_price_btc",
        btc_amount="btc_amount",
        btc_amount_partial="btc_amount_partial",
        payment_subaddress="xmr_receiving_subaddress",
        payment_address="xmr_receiving_address",
        payment_integrated_address="xmr_receiving_integrated_address",
        payment_id_long="xmr_required_payment_id_long",
        payment_id_short="xmr_required_payment_id_short",
        in_amount="xmr_amount_total",
        in_amount_remaining="xmr_amount_remaining",
        in_confirmations_remaining="xmr_num_confirmations_remaining",
        seconds_till_timeout="seconds_till_timeout",
        created_at="created_at",
    )
    V3Status = StatusClass(
        state="state",
        in_out_rate="incoming_price_btc",
        btc_amount="btc_amount",
        btc_amount_partial="btc_amount_partial",
        payment_subaddress="receiving_subaddress",
        payment_address="receiving_address",
        payment_integrated_address="receiving_integrated_address",
        payment_id_long="required_payment_id_long",
        payment_id_short="required_payment_id_short",
        in_amount="incoming_amount_total",
        in_amount_remaining="remaining_amount_incoming",
        in_confirmations_remaining="incoming_num_confirmations_remaining",
        seconds_till_timeout="seconds_till_timeout",
        created_at="created_at",
    )

    apis = {"v1": V1Status, "v2": V2Status, "v3": V3Status}
    api_classes = {"v1": StatusClass, "v2": StatusClass, "v3": StatusClass}

    @classmethod
    def get(cls, data, api):
        status = cls.apis[api]
        StatusClass_ = cls.api_classes[api]
        if not status or not data:
            return None, None

        xmrto_error = None
        if "error" in data:
            xmrto_error = data

        state = data.get(status.state, None)
        in_out_rate = data.get(status.in_out_rate, None)
        btc_amount = data.get(status.btc_amount, None)
        btc_amount_partial = data.get(status.btc_amount_partial, None)
        in_confirmations_remaining = data.get(status.in_confirmations_remaining, None)
        in_amount_remaining = data.get(status.in_amount_remaining, None)
        in_amount = data.get(status.in_amount, None)
        payment_id_short = data.get(status.payment_id_short, None)
        payment_id_long = data.get(status.payment_id_long, None)
        payment_integrated_address = data.get(status.payment_integrated_address, None)
        payment_address = data.get(status.payment_address, None)
        payment_subaddress = data.get(status.payment_subaddress, None)
        seconds_till_timeout = data.get(status.seconds_till_timeout, None)
        created_at = data.get(status.created_at, None)

        return (
            StatusClass_(
                state=state,
                in_out_rate=in_out_rate,
                btc_amount=btc_amount,
                btc_amount_partial=btc_amount_partial,
                in_confirmations_remaining=in_confirmations_remaining,
                in_amount_remaining=in_amount_remaining,
                in_amount=in_amount,
                payment_id_short=payment_id_short,
                payment_id_long=payment_id_long,
                payment_integrated_address=payment_integrated_address,
                payment_address=payment_address,
                payment_subaddress=payment_subaddress,
                seconds_till_timeout=seconds_till_timeout,
                created_at=created_at,
            ),
            xmrto_error,
        )


class CheckPrice:
    V1Price = None
    V2Price = Price(
        out_amount="btc_amount",
        in_amount="xmr_amount_total",
        in_out_rate="xmr_price_btc",
    )
    V3Price = Price(
        out_amount="btc_amount",
        in_amount="incoming_amount_total",
        in_out_rate="incoming_price_btc",
    )
    apis = {"v1": V1Price, "v2": V2Price, "v3": V3Price}

    @classmethod
    def get(cls, data, api):
        price = cls.apis[api]
        if not price or not data:
            return None

        xmrto_error = None
        if "error" in data:
            xmrto_error = data

        out_amount = data.get(price.out_amount, None)
        in_amount = data.get(price.in_amount, None)
        in_out_rate = data.get(price.in_out_rate, None)

        return (
            Price(out_amount=out_amount, in_amount=in_amount, in_out_rate=in_out_rate),
            xmrto_error,
        )


class CheckQrCode:
    @classmethod
    def get(cls, data, api):
        return data


class XmrtoApi:
    CREATE_ORDER_ENDPOINT = "/api/{api_version}/xmr2btc/order_create/"
    ORDER_STATUS_ENDPOINT = "/api/{api_version}/xmr2btc/order_status_query/"
    CHECK_PRICE_ENDPOINT = "/api/{api_version}/xmr2btc/order_check_price/"
    PARTIAL_PAYMENT_ENDPOINT = "/api/{api_version}/xmr2btc/order_partial_payment/"
    QRCODE_ENDPOINT = "/api/{api_version}/xmr2btc/gen_qrcode"

    def __init__(self, url=XMRTO_URL_DEFAULT, api=API_VERSION_DEFAULT):
        self.url = url
        self.api = api
        self.__xmr_conn = XmrtoConnection()

    def __add_amount_and_currency(self, out_amount=None, currency=None):
        additional_api_keys = {}
        amount_key = "btc_amount"
        if self.api == "v2":
            if currency == "BTC":
                amount_key = "btc_amount"
            elif currency == "XMR":
                amount_key = "xmr_amount"
        elif self.api == "v3":
            amount_key = "amount"
            additional_api_keys["amount_currency"] = currency

        additional_api_keys[f"{amount_key}"] = str(out_amount)

        return additional_api_keys

    def create_order(self, out_address=None, out_amount=None, currency="BTC"):
        if out_address is None:
            return None
        if out_amount is None:
            return None
        create_order_url = self.url + self.CREATE_ORDER_ENDPOINT.format(
            api_version=self.api
        )

        postdata = {"btc_dest_address": out_address}
        postdata.update(
            self.__add_amount_and_currency(out_amount=out_amount, currency=currency)
        )

        response = self.__xmr_conn.post(url=create_order_url, postdata=postdata)

        return CreateOrder.get(data=response, api=self.api)

    def order_status(self, uuid=None):
        if uuid is None:
            return None
        order_status_url = self.url + self.ORDER_STATUS_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"uuid": uuid}

        response = self.__xmr_conn.post(url=order_status_url, postdata=postdata)

        return OrderStatus.get(data=response, api=self.api)

    def confirm_partial_payment(self, uuid=None):
        if uuid is None:
            return None, None
        partial_payment_url = self.url + self.PARTIAL_PAYMENT_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"uuid": uuid}

        response = self.__xmr_conn.post(
            url=partial_payment_url, postdata=postdata, expect_json=False
        )

        xmrto_error = None
        confirmed = True
        if "error" in response:
            xmrto_error = response
            confirmed = False

        if not response:
            return None, None

        # if response.status_code in [codes.ok]:
        #     confirmed = False
        #     xmrto_error = {"status_code": response.status_code}

        return confirmed, xmrto_error

    def order_check_price(self, btc_amount=None, xmr_amount=None, currency="BTC"):
        if btc_amount is None and xmr_amount is None:
            return None
        if currency is None:
            return None
        order_check_price_url = self.url + self.CHECK_PRICE_ENDPOINT.format(
            api_version=self.api
        )

        if btc_amount:
            currency = "BTC"
            out_amount = btc_amount
        elif xmr_amount:
            currency = "XMR"
            out_amount = xmr_amount

        postdata = dict()
        postdata.update(
            self.__add_amount_and_currency(out_amount=out_amount, currency=currency)
        )

        response = self.__xmr_conn.post(url=order_check_price_url, postdata=postdata)

        return CheckPrice.get(data=response, api=self.api)

    def generate_qrcode(self, data=None):
        if data is None:
            return None
        generate_qrcode_url = (
            self.url
            + self.QRCODE_ENDPOINT.format(api_version=self.api)
            + f"?data={data}"
        )
        response = self.__xmr_conn.get(url=generate_qrcode_url, expect_json=False)

        return CheckQrCode.get(data=response, api=self.api)


class OrderStateType(type):
    @property
    def TO_BE_CREATED(cls):
        return "TO_BE_CREATED"

    @property
    def UNPAID(cls):
        return "UNPAID"

    @property
    def UNDERPAID(cls):
        return "UNDERPAID"

    @property
    def PAID_UNCONFIRMED(cls):
        return "PAID_UNCONFIRMED"

    @property
    def BTC_SENT(cls):
        return "BTC_SENT"

    @property
    def TIMED_OUT(cls):
        return "TIMED_OUT"

    @property
    def PURGED(cls):
        return "PURGED"

    @property
    def PURGED(cls):
        return "FLAGGED_DESTINATION_ADDRESS"


class XmrtoOrderStatus:
    def __init__(self, url=XMRTO_URL_DEFAULT, api=API_VERSION_DEFAULT, uuid=None):
        self.url = url
        self.api = api
        self.xmrto_api = XmrtoApi(url=self.url, api=self.api)
        self.uuid = uuid
        self.order_status = None
        self.error = None

        self.in_amount = None
        self.in_amount_remaining = None
        self.in_out_rate = None
        self.btc_amount = None
        self.btc_amount_partial = None
        self.payment_subaddress = None
        self.payment_address = None
        self.payment_integrated_address = None
        self.seconds_till_timeout = None
        self.created_at = None
        self.state = XmrtoOrder.TO_BE_CREATED

    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid
        else:
            self.uuid = uuid

        if not all([self.url, self.api, self.uuid]):
            logger.error("Please check the arguments.")
            return 0

        self.order_status, self.error = self.xmrto_api.order_status(uuid=uuid)

        if self.order_status:
            self.in_amount = self.order_status.in_amount
            self.in_amount_remaining = self.order_status.in_amount_remaining
            self.in_out_rate = self.order_status.in_out_rate
            self.btc_amount = self.order_status.btc_amount
            self.btc_amount_partial = self.order_status.btc_amount_partial
            self.payment_address = self.order_status.payment_address
            self.payment_subaddress = self.order_status.payment_subaddress
            self.payment_integrated_address = (
                self.order_status.payment_integrated_address
            )
            self.seconds_till_timeout = self.order_status.seconds_till_timeout
            self.created_at = self.order_status.created_at
            self.state = self.order_status.state
        return 1

    def confirm_partial_payment(self, uuid=None):
        if not self.get_order_status(uuid=uuid):
            return 0
        partial_payment_confirmed, self.error = self.xmrto_api.confirm_partial_payment(
            uuid=self.uuid
        )

    def _to_json(self):
        data = {"uuid": self.uuid, "state": self.state}
        if self.order_status:
            if self.order_status.payment_subaddress:
                data["payment_subaddress"] = self.order_status.payment_subaddress
            if self.order_status.payment_address:
                data["payment_address"] = self.order_status.payment_address
            if self.order_status.payment_integrated_address:
                data[
                    "payment_integrated_address"
                ] = self.order_status.payment_integrated_address
            if self.order_status.in_amount:
                data["in_amount"] = self.order_status.in_amount
            if self.order_status.in_amount_remaining:
                data["in_amount_remaining"] = self.order_status.in_amount_remaining
            if self.order_status.in_out_rate:
                data["in_out_rate"] = self.order_status.in_out_rate
            if self.order_status.btc_amount:
                data["btc_amount"] = self.order_status.btc_amount
            if self.order_status.btc_amount_partial:
                data["btc_amount_partial"] = self.order_status.btc_amount_partial
            if self.order_status.seconds_till_timeout:
                data["seconds_till_timeout"] = self.order_status.seconds_till_timeout
            if self.order_status.created_at:
                data["created_at"] = self.order_status.created_at

        if self.error:
            data["error"] = self.error

        return data

    def __str__(self):
        return json.dumps(self._to_json())


class XmrtoOrder(metaclass=OrderStateType):
    def __init__(
        self,
        url=XMRTO_URL_DEFAULT,
        api=API_VERSION_DEFAULT,
        out_address=None,
        btc_amount=None,
        xmr_amount=None,
    ):
        self.url = url
        self.api = api
        self.xmrto_api = XmrtoApi(url=self.url, api=self.api)
        self.order = None
        self.order_status = None
        self.error = None

        self.out_address = out_address
        self.btc_amount = btc_amount
        self.btc_amount_partial = None
        self.xmr_amount = xmr_amount
        self.out_amount = None
        self.currency = None
        self.uuid = None
        self.in_amount = None
        self.in_amount_remaining = None
        self.in_out_rate = None
        self.payment_subaddress = None
        self.payment_address = None
        self.payment_integrated_address = None
        self.state = XmrtoOrder.TO_BE_CREATED
        self.all = None

    def create_order(
        self, out_address=None, btc_amount=None, xmr_amount=None, currency="BTC"
    ):
        if out_address is None:
            out_address = self.out_address
        else:
            self.out_address = out_address
        if btc_amount is None:
            btc_amount = self.btc_amount
        else:
            self.btc_amount = btc_amount
        if xmr_amount is None:
            xmr_amount = self.xmr_amount
        else:
            self.xmr_amount = xmr_amount

        if not any([self.btc_amount, self.xmr_amount]):
            logger.debug(f"{self.btc_amount}, {self.xmr_amount}")
            logger.error("Please check the arguments.")
            return
        if not all([self.url, self.api, self.out_address]):
            logger.debug(f"{self.out_address}")
            logger.error("Please check the arguments.")
            return

        out_amount = self.btc_amount
        if btc_amount:
            currency = "BTC"
            out_amount = self.btc_amount
        elif xmr_amount:
            currency = "XMR"
            out_amount = self.xmr_amount

        self.currency = currency

        self.order, self.error = self.xmrto_api.create_order(
            out_address=self.out_address, out_amount=out_amount, currency=currency
        )
        if self.order:
            self.uuid = self.order.uuid
            self.state = self.order.state
            self.out_amount = self.order.out_amount

    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid

        if self.error:
            return

        self.order_status = XmrtoOrderStatus(url=self.url, api=self.api)
        self.order_status.get_order_status(uuid=uuid)
        if self.order_status:
            self.state = self.order_status.state
            self.in_amount = self.order_status.in_amount
            self.in_amount_remaining = self.order_status.in_amount_remaining
            self.in_out_rate = self.order_status.in_out_rate
            self.btc_amount = self.order_status.btc_amount
            self.btc_amount_partial = self.order_status.btc_amount_partial
            self.payment_subaddress = self.order_status.payment_subaddress
            self.payment_address = self.order_status.payment_address
            self.payment_integrated_address = (
                self.order_status.payment_integrated_address
            )
            self.error = self.order_status.error

    def __str__(self):
        data = {
            "uuid": self.uuid,
            "state": self.state,
            "btc_address": self.out_address,
            "btc_amount": self.out_amount,
        }

        if self.order_status:
            data.update(self.order_status._to_json())

        if self.error:
            data.update(self.error)

        return json.dumps(data)


def create_order(
    xmrto_url=XMRTO_URL,
    api_version=API_VERSION,
    out_address=DESTINATION_ADDRESS,
    btc_amount=BTC_AMOUNT,
    xmr_amount=XMR_AMOUNT,
):
    order = XmrtoOrder(
        url=xmrto_url,
        api=api_version,
        out_address=out_address,
        btc_amount=btc_amount,
        xmr_amount=xmr_amount,
    )
    order.create_order()
    logger.debug(f"XMR.to order: {order}")

    order.get_order_status()
    logger.debug(f"Order created: {order.uuid}")

    return order


def track_order(xmrto_url=XMRTO_URL, api_version=API_VERSION, uuid=SECRET_KEY):
    order_status = XmrtoOrderStatus(url=xmrto_url, api=api_version, uuid=uuid)
    order_status.get_order_status()
    return order_status


def confirm_partial_payment(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, uuid=SECRET_KEY
):
    order_status = track_order(xmrto_url=xmrto_url, api_version=api_version, uuid=uuid)
    if not order_status.state == XmrtoOrder.UNDERPAID:
        logger.warning(f"The order is not ready for a partial payment, wrong state.")
        return order_status
    else:
        order_status.confirm_partial_payment()
        logger.info(f"The partial payment was confirmed.")

    return order_status


def order_check_price(
    xmrto_url=XMRTO_URL,
    api_version=API_VERSION,
    btc_amount=BTC_AMOUNT,
    xmr_amount=XMR_AMOUNT,
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    return xmrto_api.order_check_price(btc_amount=btc_amount, xmr_amount=xmr_amount)


def generate_qrcode(xmrto_url=XMRTO_URL, api_version=API_VERSION, data=QR_DATA):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    qrcode = xmrto_api.generate_qrcode(data=data)
    if not qrcode:
        print("No data provided to convert to qrcode.")
    with open("qrcode.png", "wb") as qrcode_file:
        for chunk in qrcode:
            qrcode_file.write(chunk)
    print("Stored qrcode in qrcode.png.")


def main():
    from _version import __version__

    parser = argparse.ArgumentParser(
        description="Create a XMR.to order.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    config = argparse.ArgumentParser(add_help=False)

    config.add_argument(
        "-u", "--url", nargs="?", default=XMRTO_URL_DEFAULT, help="XMR.to url to use."
    )
    config.add_argument(
        "-a", "--api", default=API_VERSION_DEFAULT, help="API version to use."
    )

    config.add_argument("--debug", action="store_true", help="Show debug info.")
    config.add_argument("-c", "--certificate", nargs="?", help="Local certificate.")

    # subparsers
    subparsers = parser.add_subparsers(help="Order sub commands.", dest="subcommand")
    subparsers.required = True

    # Create order
    create = subparsers.add_parser(
        "create-order", parents=[config], help="Create an order."
    )
    create.add_argument(
        "-d",
        "--destination",
        required=True,
        help="Destination (BTC) address to send money to.",
    )
    group = create.add_mutually_exclusive_group(required=True)
    group.add_argument("-b", "--btc-amount", help="Amount to send in BTC.")
    group.add_argument("-x", "--xmr-amount", help="Amount to send in XMR.")

    # Track order
    track = subparsers.add_parser(
        "track-order", parents=[config], help="Track an order."
    )
    track.add_argument(
        "--secret-key", required=True, help="Existing secret key of an existing order."
    )

    # Partial payment
    partial = subparsers.add_parser(
        "confirm-partial-payment",
        parents=[config],
        help="Confirm the partial payment of  an order.",
    )
    partial.add_argument(
        "--secret-key", required=True, help="Existing secret key of an existing order."
    )

    # Create and track order
    create = subparsers.add_parser(
        "create-and-track-order", parents=[config], help="Create an order and track it."
    )
    create.add_argument(
        "-d",
        "--destination",
        required=True,
        help="Destination (BTC) address to send money to.",
    )
    group = create.add_mutually_exclusive_group(required=True)
    group.add_argument("-b", "--btc-amount", help="Amount to send in BTC.")
    group.add_argument("-x", "--xmr-amount", help="Amount to send in XMR.")

    # Recent price
    price = subparsers.add_parser("price", parents=[config], help="Get recent price.")
    group = price.add_mutually_exclusive_group(required=True)
    group.add_argument("-b", "--btc-amount", help="Amount to send in BTC.")
    group.add_argument("-x", "--xmr-amount", help="Amount to send in XMR.")

    # Create qrcode
    qrcode = subparsers.add_parser(
        "qrcode",
        parents=[config],
        help="Create a qrcode, is stored in a file called 'qrcode.png'.",
    )
    qrcode.add_argument("--data", required=True, help=".")

    args = parser.parse_args()

    cmd_create_and_track_order = False
    cmd_create_order = False
    cmd_track_order = False
    cmd_partial_payment = False
    cmd_get_price = False
    cmd_create_qrcode = False

    debug = args.debug
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.subcommand == "create-and-track-order":
        cmd_create_and_track_order = True
        destination_address = args.destination
        btc_amount = args.btc_amount
        xmr_amount = args.xmr_amount
    if args.subcommand == "create-order":
        cmd_create_order = True
        destination_address = args.destination
        btc_amount = args.btc_amount
        xmr_amount = args.xmr_amount
    elif args.subcommand == "track-order":
        cmd_track_order = True
        secret_key = args.secret_key
    elif args.subcommand == "confirm-partial-payment":
        cmd_partial_payment = True
        secret_key = args.secret_key
    elif args.subcommand == "price":
        cmd_get_price = True
        btc_amount = args.btc_amount
        xmr_amount = args.xmr_amount
    elif args.subcommand == "qrcode":
        cmd_create_qrcode = True
        qr_data = args.data

    xmrto_url = args.url
    api_version = args.api
    certificate = args.certificate

    if cmd_create_and_track_order:
        try:
            order = create_order(
                xmrto_url=xmrto_url,
                api_version=api_version,
                out_address=destination_address,
                btc_amount=btc_amount,
                xmr_amount=xmr_amount,
            )

            order.get_order_status()
            total = 2
            if order:
                while not order.state == XmrtoOrder.BTC_SENT:
                    print(order)
                    if order.state in (XmrtoOrder.UNPAID, XmrtoOrder.UNDERPAID):
                        print("Pay with subaddress.")
                        print(
                            f"    transfer {order.order_status.payment_subaddress} {order.order_status.in_amount_remaining}"
                        )
                        if order.order_status.payment_integrated_address:
                            print("Pay with integrated address")
                            print(
                                f"    transfer {order.order_status.payment_integrated_address} {order.order_status.in_amount_remaining}"
                            )
                    if order.state == XmrtoOrder.TIMED_OUT:
                        total -= 1
                        if total == 0:
                            break
                    time.sleep(3)
                    order.get_order_status()
                print(order)
        except (KeyboardInterrupt) as e:
            print(f"\nUser interrupted")
            if order:
                print(f"{order}")
    elif cmd_create_order:
        order = create_order(
            xmrto_url=xmrto_url,
            api_version=api_version,
            out_address=destination_address,
            btc_amount=btc_amount,
            xmr_amount=xmr_amount,
        )

        print(order)
    elif cmd_track_order:
        order_status = track_order(
            xmrto_url=xmrto_url, api_version=api_version, uuid=secret_key
        )
        print(order_status)
        if order_status.state in (XmrtoOrder.UNPAID, XmrtoOrder.UNDERPAID):
            print("Pay with subaddress.")
            print(
                f"    transfer {order_status.payment_subaddress} {order_status.in_amount_remaining}"
            )
            if order_status.payment_integrated_address:
                print("Pay with integrated address")
                print(
                    f"    transfer {order_status.payment_integrated_address} {order_status.in_amount_remaining}"
                )
    elif cmd_partial_payment:
        order_status = confirm_partial_payment(
            xmrto_url=xmrto_url, api_version=api_version, uuid=secret_key
        )
        print(order_status)
    elif cmd_get_price:
        price, error = order_check_price(
            xmrto_url=xmrto_url,
            api_version=api_version,
            btc_amount=btc_amount,
            xmr_amount=xmr_amount,
        )

        if error:
            print(error)
            return

        print(price)
    elif cmd_create_qrcode:
        generate_qrcode(xmrto_url=xmrto_url, api_version=api_version, data=qr_data)


if __name__ == "__main__":
    sys.exit(main())
