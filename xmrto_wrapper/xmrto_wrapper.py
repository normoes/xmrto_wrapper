#!/usr/bin/env python

"""
Goal:
  * Interact with XMR.to.

How to:
  * General usage
    - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
    - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001` --follow
    - `python xmrto_wrapper.py track-order --secret-key xmrto-ebmA9q`
    - `python xmrto_wrapper.py track-order --secret-key xmrto-ebmA9q` --follow
    - `python xmrto_wrapper.py check-price --btc-amount 0.01`
    - `python xmrto_wrapper.py parameters`
    - `python xmrto_wrapper.py qrcode --data "something"`
  * Get help
    - xmrto_wrapper.py -h
  * You can
    - Create an order: `xmrto_wrapper.py create-order`
    - Track an order: `xmrto_wrapper.py track-order`
    - Get a recent price: `xmrto_wrapper.py price`
    - Create a QR code: `xmrto_wrapper.py qrcode`
  * The default API used is `--api v2`, so no need to actually set that parameter.
  * The default URL used is `--url https://xmr.to`, so no need to actually set that parameter.

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
import re
from typing import List, Dict
from dataclasses import dataclass
from types import SimpleNamespace

from requests import Session, codes
from requests.exceptions import ConnectionError, SSLError


logging.basicConfig()
logger = logging.getLogger("XmrtoWrapper")
logger.setLevel(logging.INFO)

API_VERSIONS_ = {
    "v2": "v2",
    "v3": "v3",
}
API_VERSIONS = SimpleNamespace(**API_VERSIONS_)

XMRTO_URL_DEFAULT = "https://xmr.to"
API_VERSION_DEFAULT = API_VERSIONS.v3

XMRTO_URL = os.environ.get("XMRTO_URL", XMRTO_URL_DEFAULT)
API_VERSION = os.environ.get("API_VERSION", API_VERSION_DEFAULT)
DESTINATION_ADDRESS = os.environ.get("BTC_ADDRESS", None)
LN_INVOICE = os.environ.get("LN_INVOICE", None)
BTC_AMOUNT = os.environ.get("BTC_AMOUNT", None)
XMR_AMOUNT = os.environ.get("XMR_AMOUNT", None)
CERTIFICATE = os.environ.get("XMRTO_CERTIFICATE", None)
QR_DATA = os.environ.get("QR_DATA", None)
SECRET_KEY = os.environ.get("SECRET_KEY", None)


@dataclass
class StatusAttributes:
    state: str = "state"
    out_amount: str = "btc_amount"
    out_amount_partial: str = "btc_amount_partial"
    out_address: str = "btc_dest_address"
    seconds_till_timeout: str = "seconds_till_timeout"
    created_at: str = "created_at"
    # Difference between API versions.
    in_out_rate: str = "xmr_price_btc"
    payment_subaddress: str = "xmr_receiving_subaddress"
    in_amount: str = "xmr_amount_total"
    in_amount_remaining: str = "xmr_amount_remaining"
    in_confirmations_remaining: str = "xmr_num_confirmations_remaining"


@dataclass
class StatusAttributesV2(StatusAttributes):
    # Only with API v2.
    payment_address: str = "xmr_receiving_address"
    payment_integrated_address: str = "xmr_receiving_integrated_address"
    payment_id_long: str = "xmr_required_payment_id_long"
    payment_id_short: str = "xmr_required_payment_id_short"


@dataclass
class StatusAttributesV3(StatusAttributes):
    in_out_rate: str = "incoming_price_btc"
    payment_subaddress: str = "receiving_subaddress"
    in_amount: str = "incoming_amount_total"
    in_amount_remaining: str = "remaining_amount_incoming"
    in_confirmations_remaining: str = "incoming_num_confirmations_remaining"
    # Only with API v3.
    uses_lightning: str = "uses_lightning"
    payments: str = "payments"


@dataclass
class Status:
    state: str = ""
    out_amount: float = 0.0
    out_amount_partial: float = 0.0
    out_address: str = ""
    seconds_till_timeout: int = 0
    created_at: str = ""
    # Difference between API versions.
    in_out_rate: float = 0.0
    payment_subaddress: str = ""
    in_amount: float = 0.0
    in_amount_remaining: float = 0.0
    in_confirmations_remaining: int = 0


@dataclass
class StatusV2(Status):
    # Only with API v2.
    payment_address: str = ""
    payment_integrated_address: str = ""
    payment_id_long: str = ""
    payment_id_short: str = ""
    attributes = StatusAttributesV2()


@dataclass
class StatusV3(Status):
    out_amount: str = "0.0"
    out_amount_partial: str = "0.0"
    in_out_rate: str = "0.0"
    in_amount: str = "0.0"
    in_amount_remaining: str = "0.0"
    uses_lightning: bool = False
    payments: List[Dict] = None
    attributes = StatusAttributesV3()


@dataclass
class OrderAttributes:
    uuid: str = "uuid"
    state: str = "state"
    out_address: str = "btc_dest_address"
    out_amount: str = "btc_amount"


@dataclass
class OrderAttributesV3(OrderAttributes):
    # Only with API v3.
    uses_lightning: str = "uses_lightning"


@dataclass
class Order:
    uuid: str = ""
    state: str = ""
    out_amount: float = 0.0
    out_address: str = ""


@dataclass
class OrderV2(Order):
    attributes = OrderAttributes()


@dataclass
class OrderV3(Order):
    uses_lightning: bool = False
    attributes = OrderAttributesV3()


PRICE_FIELDS = ("out_amount", "in_amount", "in_out_rate")
Price = collections.namedtuple("Price", PRICE_FIELDS)


@dataclass
class PriceAttributes:
    out_amount: str = "btc_amount"


@dataclass
class PriceAttributesV2(PriceAttributes):
    in_amount: str = "xmr_amount_total"
    in_out_rate: str = "xmr_price_btc"
    in_num_confirmations_remaining: str = "xmr_num_confirmations_remaining"


@dataclass
class PriceAttributesV3(PriceAttributes):
    in_amount: str = "incoming_amount_total"
    in_out_rate: str = "incoming_price_btc"
    in_num_confirmations_remaining: str = "incoming_num_confirmations_remaining"


@dataclass
class Price:
    def _to_json(self):
        data = {PriceAttributes.out_amount: self.out_amount}
        return data

    def __str__(self):
        return json.dumps(self._to_json())


@dataclass
class PriceV2(Price):
    out_amount: float = 0.0
    in_amount: float = 0.0
    in_out_rate: float = 0.0
    in_num_confirmations_remaining: int = -1
    attributes = PriceAttributesV2()

    def _to_json(self):
        data = super()._to_json()
        data.update({PriceAttributesV2.in_amount: self.in_amount})
        data.update({PriceAttributesV2.in_out_rate: self.in_out_rate})
        data.update(
            {
                PriceAttributesV2.in_num_confirmations_remaining: self.in_num_confirmations_remaining
            }
        )
        return data

    def __str__(self):
        return json.dumps(self._to_json())


@dataclass
class PriceV3(Price):
    out_amount: str = "0.0"
    xmr_amount: str = "0.0"
    in_out_rate: str = "0.0"
    in_num_confirmations_remaining: int = -1
    attributes = PriceAttributesV3()

    def _to_json(self):
        data = super()._to_json()
        data.update({PriceAttributesV3.in_amount: self.in_amount})
        data.update({PriceAttributesV3.in_out_rate: self.in_out_rate})
        data.update(
            {
                PriceAttributesV3.in_num_confirmations_remaining: self.in_num_confirmations_remaining
            }
        )
        return data

    def __str__(self):
        return json.dumps(self._to_json())


@dataclass
class RoutesAttributes:
    num_routes: str = "num_routes"
    success_probability: str = "success_probability"


@dataclass
class Routes:
    num_routes: int = 0
    success_probability: float = 0.0
    attributes = RoutesAttributes()


@dataclass
class ParametersAttributes:
    price: str = "price"
    upper_limit: str = "upper_limit"
    lower_limit: str = "lower_limit"
    zero_conf_max_amount: str = "zero_conf_max_amount"
    zero_conf_enabled: bool = "zero_conf_enabled"


@dataclass
class ParametersAttributesV2(ParametersAttributes):
    pass


@dataclass
class ParametersAttributesV3(ParametersAttributes):
    ln_upper_limit: str = "ln_upper_limit"
    ln_lower_limit: str = "ln_lower_limit"


@dataclass
class Parameters:
    zero_conf_enabled: bool = False

    def _to_json(self):
        data = {ParametersAttributes.zero_conf_enabled: self.zero_conf_enabled}
        return data

    def __str__(self):
        return json.dumps(self._to_json())


@dataclass
class ParametersV2(Parameters):
    price: float = 0.0
    upper_limit: float = 0.0
    lower_limit: float = 0.0
    zero_conf_max_amount: float = 0.0
    attributes = ParametersAttributesV2()

    def _to_json(self):
        data = super()._to_json()
        data.update({ParametersAttributesV2.price: self.price})
        data.update({ParametersAttributesV2.upper_limit: self.upper_limit})
        data.update({ParametersAttributesV2.lower_limit: self.lower_limit})
        data.update(
            {
                ParametersAttributesV2.zero_conf_max_amount: self.zero_conf_max_amount
            }
        )
        return data

    def __str__(self):
        return json.dumps(self._to_json())


@dataclass
class ParametersV3(Parameters):
    price: str = "0.0"
    upper_limit: str = "0.0"
    lower_limit: str = "0.0"
    ln_upper_limit: str = "0.0"
    ln_lower_limit: str = "0.0"
    zero_conf_max_amount: str = "0.0"
    attributes = ParametersAttributesV3()

    def _to_json(self):
        data = super()._to_json()
        data.update({ParametersAttributesV3.price: self.price})
        data.update({ParametersAttributesV3.upper_limit: self.upper_limit})
        data.update({ParametersAttributesV3.lower_limit: self.lower_limit})
        data.update(
            {ParametersAttributesV3.ln_upper_limit: self.ln_upper_limit}
        )
        data.update(
            {ParametersAttributesV3.ln_lower_limit: self.ln_lower_limit}
        )
        data.update(
            {
                ParametersAttributesV3.zero_conf_max_amount: self.zero_conf_max_amount
            }
        )
        return data

    def __str__(self):
        return json.dumps(self._to_json())


# PARAMETERS_FIELDS = ("price", "upper_limit", "lower_limit", "ln_upper_limit", "ln_lower_limit", "zero_conf_enabled", "zero_conf_max_amount")
# Parameters = collections.namedtuple("Parameters", PARAMETERS_FIELDS)


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

    def post(
        self,
        url: str,
        postdata: Dict[str, str],
        expect_json=True,
        expect_response=True,
    ):
        return self._request(
            url=url,
            func=self._post,
            postdata=postdata,
            expect_json=expect_json,
            expect_response=expect_response,
        )

    def _post(self, url: str, postdata: str, **kwargs):
        logger.debug(f"--> POSTDATA: {postdata}.")
        logger.debug(f"--> Additional request arguments: '{kwargs}'.")
        return self.__conn.post(
            url=url,
            data=postdata,
            timeout=self.__timeout,
            **kwargs,  # , allow_redirects=False
        )

    def _request(
        self,
        url: str,
        func,
        postdata: Dict[str, str] = None,
        expect_json=True,
        expect_response=True,
    ):
        """Makes the HTTP request

        """

        url = url.lower()
        if url.find("localhost") < 0:
            schema = re.compile("http[s]?://")
            if not schema.match(
                url
            ):  # 'match' starts at the begining of the line.
                url = "https://" + url
            http = re.compile("http://")
            if http.match(url):  # 'match' starts at the begining of the line.
                url = url.replace("http", "https")

        logger.debug(f"--> URL: {url}")

        response = None
        try:
            try:
                data = {"url": url}
                if postdata:
                    data["postdata"] = json.dumps(postdata)

                response = func(**data)
                logger.debug(f"--> METHOD: {response.request.method}.")
                logger.debug(f"--> HEADERS: {response.request.headers}.")
            except (SSLError) as e:
                # Disable verification: verify=False
                # , cert=path_to_certificate
                # , verify=True
                logger.debug(
                    f"Trying certificate: '{CERTIFICATE}'. SSL certificate error '{str(e)}'."
                )
                data["cert"] = CERTIFICATE
                data["verify"] = True

                response = func(**data)
        except (ConnectionError) as e:
            logger.debug(f"Connection error: {str(e)}.")
            error_msg = {"error": str(e)}
            error_msg["url"] = url
            error_msg["error_code"] = 102
            logger.error(json.dumps(error_msg))
            return error_msg
        except (Exception) as e:
            logger.debug(f"Error: {str(e)}.")
            error_msg = {"error": str(e)}
            error_msg["url"] = url
            error_msg["error_code"] = 103
            logger.error(json.dumps(error_msg))
            return error_msg

        response_ = None
        try:
            response_ = self._get_response(
                response=response, expect_json=expect_json
            )
        except (ValueError) as e:
            logger.debug(f"Error: {str(e)}.")
            error_msg = {"error": json.loads(str(e))}
            error_msg["url"] = url
            error_msg["error_code"] = 100
            logger.error(f"Response error: {json.dumps(error_msg)}.")
            return error_msg

        if not response_:
            error_msg = {"error": "Could not evaluate response."}
            error_msg["url"] = url
            error_msg["error_code"] = 101
            if expect_response:
                logger.error(f"No response: {json.dumps(error_msg)}.")
            else:
                logger.debug(
                    f"No response: {json.dumps(error_msg)}. No response expected, ignored."
                )
            return error_msg
        elif isinstance(response_, dict) and (
            not response_.get("error", None) is None
        ):
            error_msg = response_
            error_msg["url"] = url
            logger.error(f"API error: {json.dumps(error_msg)}.")
            return error_msg

        return response_

    def _get_response(self, response, expect_json=True):
        """Evaluate HTTP request response

        :return: Either JSON response or response object in case of PNG (QRCode)
        """

        json_response = None

        # Compare against None
        # Response with 400 status code returns True for not response
        if response is None:
            json_response = {
                "error": "No response.",
                "error_msg": f"Response is {response}.",
            }

        if not json_response:
            logger.debug(f"<-- STATUS CODE: {response.status_code}.")
            # Error codes used by the API, returning API errors.
            if response.status_code not in (
                codes.ok,
                codes.created,  # Order created.
                codes.bad,  # Invalid post parameters.
                codes.forbidden,  # Rate limit.
                codes.not_found,  # Order not found.
            ):
                json_response = {
                    "error": "HTTP status code.",
                    "error_msg": f"Received HTTP status code: {response.status_code}.",
                }

        if not json_response:
            http_response = response.text
            if http_response is None:
                json_response = {
                    "error": "Empty response.",
                    "error_msg": "Missing HTTP response from server.",
                }

        if not json_response:
            try:
                json_response = response.json()
            except (json.decoder.JSONDecodeError) as e:
                if expect_json:
                    if response.status_code in (
                        codes.not_found,  # General 'not found', e.g. API endpoint not found.
                    ):
                        json_response = {
                            "error": "HTTP status code.",
                            "error_msg": f"Received HTTP status code: {response.status_code}.",
                        }
                    else:
                        json_response = {
                            "error": "Expected JSON, got something else.",
                            "error_msg": str(e),
                            "response": http_response,
                        }
                else:
                    return http_response

        logger.debug(f"<-- {json_response}")

        return json_response


class CreateOrder:
    api_classes = {API_VERSIONS.v2: OrderV2, API_VERSIONS.v3: OrderV3}

    @classmethod
    def get(cls, data, api):

        xmrto_error = None
        if data and "error" in data:
            xmrto_error = data

        order_ = cls.api_classes[api]

        if not order_ or not data:
            return None, xmrto_error

        order = order_()

        order.uuid = data.get(order.attributes.uuid, None)
        order.state = data.get(order.attributes.state, None)
        order.out_address = data.get(order.attributes.out_address, None)
        order.out_amount = data.get(order.attributes.out_amount, None)

        if api == API_VERSIONS.v3:
            order.uses_lightning = data.get(
                order.attributes.uses_lightning, None
            )

        return order, xmrto_error


class OrderStatus:
    api_classes = {API_VERSIONS.v2: StatusV2, API_VERSIONS.v3: StatusV3}

    @classmethod
    def get(cls, data, api):

        xmrto_error = None
        if data and "error" in data:
            xmrto_error = data

        status_ = cls.api_classes[api]

        if not status_ or not data:
            return None, xmrto_error

        status = status_()

        status.state = data.get(status.attributes.state, None)
        status.in_out_rate = data.get(status.attributes.in_out_rate, None)
        status.out_amount = data.get(status.attributes.out_amount, None)
        status.out_amount_partial = data.get(
            status.attributes.out_amount_partial, None
        )
        status.out_address = data.get(status.attributes.out_address, None)
        status.in_confirmations_remaining = data.get(
            status.attributes.in_confirmations_remaining, None
        )
        status.in_amount_remaining = data.get(
            status.attributes.in_amount_remaining, None
        )
        status.in_amount = data.get(status.attributes.in_amount, None)
        status.payment_subaddress = data.get(
            status.attributes.payment_subaddress, None
        )
        status.seconds_till_timeout = data.get(
            status.attributes.seconds_till_timeout, None
        )
        status.created_at = data.get(status.attributes.created_at, None)

        if api == API_VERSIONS.v2:
            status.payment_address = data.get(
                status.attributes.payment_address, None
            )
            status.payment_integrated_address = data.get(
                status.attributes.payment_integrated_address, None
            )
            status.payment_id_short = data.get(
                status.attributes.payment_id_short, None
            )
            status.payment_id_long = data.get(
                status.attributes.payment_id_long, None
            )

        if api == API_VERSIONS.v3:
            status.uses_lightning = data.get(
                status.attributes.uses_lightning, None
            )
            status.payments = data.get(status.attributes.payments, None)

        return (
            status,
            xmrto_error,
        )


class CheckPrice:
    api_classes = {API_VERSIONS.v2: PriceV2, API_VERSIONS.v3: PriceV3}

    @classmethod
    def get(cls, data, api):

        xmrto_error = None
        if data and "error" in data:
            xmrto_error = data

        price_ = cls.api_classes[api]

        if not price_ or not data:
            return None, xmrto_error

        price = price_()

        price.out_amount = data.get(price.attributes.out_amount, None)
        price.in_amount = data.get(price.attributes.in_amount, None)
        price.in_out_rate = data.get(price.attributes.in_out_rate, None)
        price.in_num_confirmations_remaining = data.get(
            price.attributes.in_num_confirmations_remaining, None
        )

        return (
            price,
            xmrto_error,
        )


class CheckRoutes:
    api_classes = {API_VERSIONS.v2: None, API_VERSIONS.v3: Routes}

    @classmethod
    def get(cls, data, api):

        xmrto_error = None
        if data and "error" in data:
            xmrto_error = data

        routes_ = cls.api_classes[api]

        if not routes_ or not data:
            return None, xmrto_error

        routes = routes_()

        routes.num_routes = data.get(routes.attributes.num_routes, None)
        routes.success_probability = data.get(
            routes.attributes.success_probability, None
        )

        return (
            routes,
            xmrto_error,
        )


class CheckParameters:
    api_classes = {
        API_VERSIONS.v2: ParametersV2,
        API_VERSIONS.v3: ParametersV3,
    }

    @classmethod
    def get(cls, data, api):

        xmrto_error = None
        if data and "error" in data:
            xmrto_error = data

        parameters_ = cls.api_classes[api]

        if not parameters_ or not data:
            return None, xmrto_error

        parameters = parameters_()

        parameters.price = data.get(parameters.attributes.price, None)
        parameters.upper_limit = data.get(
            parameters.attributes.upper_limit, None
        )
        parameters.lower_limit = data.get(
            parameters.attributes.lower_limit, None
        )
        parameters.zero_conf_enabled = data.get(
            parameters.attributes.zero_conf_enabled, None
        )
        parameters.zero_conf_max_amount = data.get(
            parameters.attributes.zero_conf_max_amount, None
        )

        if api == API_VERSIONS.v3:
            parameters.ln_upper_limit = data.get(
                parameters.attributes.ln_upper_limit, None
            )
            parameters.ln_lower_limit = data.get(
                parameters.attributes.ln_lower_limit, None
            )

        return (
            parameters,
            xmrto_error,
        )


class CheckQrCode:
    @classmethod
    def get(cls, data, api):
        return data


class XmrtoApi:
    CREATE_ORDER_ENDPOINT = "/api/{api_version}/xmr2btc/order_create/"
    CREATE_LN_ORDER_ENDPOINT = "/api/{api_version}/xmr2btc/order_create_ln/"
    ORDER_STATUS_ENDPOINT = "/api/{api_version}/xmr2btc/order_status_query/"
    CHECK_PRICE_ENDPOINT = "/api/{api_version}/xmr2btc/order_check_price/"
    CHECK_LN_ROUTES_ENDPOINT = (
        "/api/{api_version}/xmr2btc/order_ln_check_route/"
    )
    CHECK_PARAMETERS_ENDPOINT = (
        "/api/{api_version}/xmr2btc/order_parameter_query/"
    )
    PARTIAL_PAYMENT_ENDPOINT = (
        "/api/{api_version}/xmr2btc/order_partial_payment/"
    )
    QRCODE_ENDPOINT = "/api/{api_version}/xmr2btc/gen_qrcode"

    def __init__(self, url=XMRTO_URL_DEFAULT, api=API_VERSION_DEFAULT):
        self.url = url[:-1] if url.endswith("/") else url
        self.api = api
        self.__xmr_conn = XmrtoConnection()

    def __add_amount_and_currency(self, out_amount=None, currency=None):
        additional_api_keys = {}
        amount_key = "btc_amount"
        if self.api == API_VERSIONS.v2:
            if currency == "BTC":
                amount_key = "btc_amount"
            elif currency == "XMR":
                amount_key = "xmr_amount"
        elif self.api == API_VERSIONS.v3:
            amount_key = "amount"
            additional_api_keys["amount_currency"] = currency

        additional_api_keys[f"{amount_key}"] = str(out_amount)

        return additional_api_keys

    def create_order(self, out_address=None, out_amount=None, currency="BTC"):
        if out_address is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--destination', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        if out_amount is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--btc-amount' or '--xmr-amount', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        create_order_url = self.url + self.CREATE_ORDER_ENDPOINT.format(
            api_version=self.api
        )

        postdata = {"btc_dest_address": out_address}
        postdata.update(
            self.__add_amount_and_currency(
                out_amount=out_amount, currency=currency
            )
        )

        response = self.__xmr_conn.post(
            url=create_order_url, postdata=postdata
        )

        return CreateOrder.get(data=response, api=self.api)

    def create_ln_order(self, ln_invoice=None):
        if ln_invoice is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--invoice', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        create_order_url = self.url + self.CREATE_LN_ORDER_ENDPOINT.format(
            api_version=self.api
        )

        postdata = {"ln_invoice": ln_invoice}

        response = self.__xmr_conn.post(
            url=create_order_url, postdata=postdata
        )

        return CreateOrder.get(data=response, api=self.api)

    def order_status(self, uuid=None):
        if uuid is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--secret-key', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        order_status_url = self.url + self.ORDER_STATUS_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"uuid": uuid}

        response = self.__xmr_conn.post(
            url=order_status_url, postdata=postdata
        )

        return OrderStatus.get(data=response, api=self.api)

    def confirm_partial_payment(self, uuid=None):
        if uuid is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--secret-key', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        partial_payment_url = self.url + self.PARTIAL_PAYMENT_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"uuid": uuid}

        response = self.__xmr_conn.post(
            url=partial_payment_url,
            postdata=postdata,
            expect_json=False,
            expect_response=False,
        )

        xmrto_error = None
        confirmed = True
        if response and "error" in response:
            xmrto_error = response
            confirmed = False

        if not response:
            return False, xmrto_error

        return confirmed, xmrto_error

    def order_check_price(
        self, btc_amount=None, xmr_amount=None, currency="BTC"
    ):
        if btc_amount is None and xmr_amount is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument --'btc-amount' or '--xmr-amount', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        order_check_price_url = self.url + self.CHECK_PRICE_ENDPOINT.format(
            api_version=self.api
        )

        if btc_amount:
            currency = "BTC"
            out_amount = btc_amount
        elif xmr_amount:
            currency = "XMR"
            out_amount = xmr_amount

        postdata = {}
        postdata.update(
            self.__add_amount_and_currency(
                out_amount=out_amount, currency=currency
            )
        )

        response = self.__xmr_conn.post(
            url=order_check_price_url, postdata=postdata
        )

        return CheckPrice.get(data=response, api=self.api)

    def order_check_ln_routes(self, ln_invoice=None):
        logger.debug(ln_invoice)
        if ln_invoice is None:
            error = {
                "error": "Argument missing.",
                "error_msg": "Expected argument '--invoice', see 'python xmrto-wrapper.py -h'.",
            }
            return None, error
        order_check_ln_routes_url = (
            self.url
            + self.CHECK_LN_ROUTES_ENDPOINT.format(api_version=self.api)
        )

        query_param = f"?ln_invoice={ln_invoice}"

        response = self.__xmr_conn.get(
            url=order_check_ln_routes_url + query_param
        )

        return CheckRoutes.get(data=response, api=self.api)

    def order_check_parameters(self):
        order_check_parameters_url = (
            self.url
            + self.CHECK_PARAMETERS_ENDPOINT.format(api_version=self.api)
        )

        response = self.__xmr_conn.get(url=order_check_parameters_url)

        return CheckParameters.get(data=response, api=self.api)

    def generate_qrcode(self, data=None):
        if data is None:
            return None
        generate_qrcode_url = (
            self.url
            + self.QRCODE_ENDPOINT.format(api_version=self.api)
            + f"?data={data}"
        )
        response = self.__xmr_conn.get(
            url=generate_qrcode_url, expect_json=False
        )

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
    def FLAGGED_DESTINATION_ADDRESS(cls):
        return "FLAGGED_DESTINATION_ADDRESS"


class XmrtoOrderStatus:
    def __init__(
        self, url=XMRTO_URL_DEFAULT, api=API_VERSION_DEFAULT, uuid=None
    ):
        self.url = url[:-1] if url.endswith("/") else url
        self.api = api
        self.xmrto_api = XmrtoApi(url=self.url, api=self.api)
        self.uuid = uuid
        self.order_status = None
        self.error = None

        self.in_amount = None
        self.in_amount_remaining = None
        self.in_out_rate = None
        self.out_amount = None
        self.out_amount_partial = None
        self.out_address = None
        self.payment_subaddress = None
        self.payment_address = None
        self.payment_integrated_address = None
        self.seconds_till_timeout = None
        self.created_at = None
        self.in_confirmations_remaining = None
        self.payments = None
        self.state = XmrtoOrder.TO_BE_CREATED

    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid
        else:
            self.uuid = uuid

        if not all([self.url, self.api, self.uuid]):
            logger.error("Please check the arguments.")
            return False

        self.order_status, self.error = self.xmrto_api.order_status(uuid=uuid)

        if self.order_status:
            self.state = self.order_status.state
            self.in_amount = self.order_status.in_amount
            self.in_amount_remaining = self.order_status.in_amount_remaining
            self.in_out_rate = self.order_status.in_out_rate
            self.out_amount = self.order_status.out_amount
            self.out_amount_partial = self.order_status.out_amount_partial
            self.out_address = self.order_status.out_address
            self.payment_subaddress = self.order_status.payment_subaddress
            self.seconds_till_timeout = self.order_status.seconds_till_timeout
            self.created_at = self.order_status.created_at
            self.in_confirmations_remaining = (
                self.order_status.in_confirmations_remaining
            )

            if self.api == API_VERSIONS.v2:
                self.payment_address = self.order_status.payment_address
                self.payment_integrated_address = (
                    self.order_status.payment_integrated_address
                )

            if self.api == API_VERSIONS.v3:
                self.payments = self.order_status.payments
        return True

    def confirm_partial_payment(self, uuid=None):
        if not self.get_order_status(uuid=uuid):
            return False
        partial_payment_confirmed = self.xmrto_api.confirm_partial_payment(
            uuid=self.uuid
        )

        return partial_payment_confirmed

    def _to_json(self):
        data = {}

        if self.uuid:
            data.update({OrderAttributesV3.uuid: self.uuid})

        if self.state:
            data.update({OrderAttributesV3.state: self.state})

        if self.out_address:
            data.update({StatusAttributesV3.out_address: self.out_address})

        if self.out_amount:
            data.update({StatusAttributesV3.out_amount: self.out_amount})

        if self.payment_subaddress:
            data[
                StatusAttributesV3.payment_subaddress
            ] = self.payment_subaddress
        if self.payment_address:
            data[StatusAttributesV2.payment_address] = self.payment_address
        if self.payment_integrated_address:
            data[
                StatusAttributesV2.payment_integrated_address
            ] = self.payment_integrated_address
        if self.in_amount:
            data[StatusAttributesV3.in_amount] = self.in_amount
        if self.in_amount_remaining:
            data[
                StatusAttributesV3.in_amount_remaining
            ] = self.in_amount_remaining
        if self.in_out_rate:
            data[StatusAttributesV3.in_out_rate] = self.in_out_rate
        if self.out_amount:
            data[StatusAttributesV3.out_amount] = self.out_amount
        if self.out_amount_partial:
            data[
                StatusAttributesV3.out_amount_partial
            ] = self.out_amount_partial
        if self.seconds_till_timeout:
            data[
                StatusAttributesV3.seconds_till_timeout
            ] = self.seconds_till_timeout
        if self.created_at:
            data[StatusAttributesV3.created_at] = self.created_at
        if (
            self.in_confirmations_remaining
            and self.in_confirmations_remaining > 0
        ):
            data[
                StatusAttributesV3.in_confirmations_remaining
            ] = self.in_confirmations_remaining

        if self.payments:
            data.update({StatusAttributesV3.payments: self.payments})

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
        self.url = url[:-1] if url.endswith("/") else url
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
        self.uses_lightning = None
        self.state = XmrtoOrder.TO_BE_CREATED

    def create_order(
        self,
        out_address=None,
        btc_amount=None,
        xmr_amount=None,
        currency="BTC",
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

        logger.debug(f"{self.btc_amount} [{currency}] to {self.out_address}.")
        self.order, self.error = self.xmrto_api.create_order(
            out_address=self.out_address,
            out_amount=out_amount,
            currency=currency,
        )
        if self.order:
            self.uuid = self.order.uuid
            self.state = self.order.state
            self.out_amount = self.order.out_amount
            self.out_address = self.order.out_address
            if self.api == API_VERSIONS.v3:
                self.uses_lightning = self.order.uses_lightning

    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid

        if self.error:
            return 1

        self.order_status = XmrtoOrderStatus(url=self.url, api=self.api)
        self.order_status.get_order_status(uuid=uuid)
        if self.order_status:
            self.state = self.order_status.state
            self.in_amount = self.order_status.in_amount
            self.in_amount_remaining = self.order_status.in_amount_remaining
            self.in_out_rate = self.order_status.in_out_rate
            self.out_amount = self.order_status.out_amount
            self.btc_amount_partial = self.order_status.out_amount_partial
            self.payment_subaddress = self.order_status.payment_subaddress
            if self.api == API_VERSIONS.v3:
                self.payments = self.order_status.payments

            self.error = self.order_status.error

    def _to_json(self):
        data = {}

        if self.uuid:
            data.update({OrderAttributesV3.uuid: self.uuid})

        if self.state:
            data.update({OrderAttributesV3.state: self.state})

        if self.out_address:
            data.update({OrderAttributesV3.out_address: self.out_address})

        if self.out_amount:
            data.update({OrderAttributesV3.out_amount: self.out_amount})

        if self.uses_lightning is not None:
            data.update(
                {OrderAttributesV3.uses_lightning: self.uses_lightning}
            )

        if self.order_status:
            data.update(self.order_status._to_json())

        if self.error:
            data.update(self.error)

        return data

    def __str__(self):
        return json.dumps(self._to_json())


class XmrtoLnOrder(XmrtoOrder):
    def __init__(
        self, url=XMRTO_URL_DEFAULT, api=API_VERSION_DEFAULT, ln_invoice=None,
    ):
        super().__init__(url=url, api=api)
        self.ln_invoice = ln_invoice

    def create_order(self, ln_invoice=None):
        if ln_invoice is None:
            ln_invoice = self.ln_invoice
        else:
            self.ln_invoice = ln_invoice

        if not all([self.url, self.api, self.ln_invoice]):
            logger.debug(f"{self.ln_invoice}")
            logger.error("Please check the arguments.")
            return

        logger.debug(f"{self.ln_invoice}")
        self.order, self.error = self.xmrto_api.create_ln_order(
            ln_invoice=self.ln_invoice
        )
        if self.order:
            self.uuid = self.order.uuid
            self.state = self.order.state
            self.out_amount = self.order.out_amount
            self.out_address = self.order.out_address


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

    logger.debug(f"Order created: {order}")

    return order


def create_ln_order(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, ln_invoice=LN_INVOICE,
):
    order = XmrtoLnOrder(
        url=xmrto_url, api=api_version, ln_invoice=ln_invoice,
    )
    order.create_order()
    logger.debug(f"XMR.to order: {order}")

    order.get_order_status()

    logger.debug(f"Order created: {order}")

    return order


def track_order(xmrto_url=XMRTO_URL, api_version=API_VERSION, uuid=SECRET_KEY):
    order_status = XmrtoOrderStatus(url=xmrto_url, api=api_version, uuid=uuid)
    order_status.get_order_status()
    return order_status


def confirm_partial_payment(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, uuid=SECRET_KEY
):
    order_status = track_order(
        xmrto_url=xmrto_url, api_version=api_version, uuid=uuid
    )
    if not order_status.state == XmrtoOrder.UNDERPAID:
        logger.warning(
            f"The order is not ready for a partial payment, wrong state."
        )
        return order_status
    else:
        partial_payment_confirmed = order_status.confirm_partial_payment()
        if not partial_payment_confirmed:
            logger.error("The partial payment was not confirmed.")
        else:
            logger.info("The partial payment was confirmed.")

    return order_status


def order_check_price(
    xmrto_url=XMRTO_URL,
    api_version=API_VERSION,
    btc_amount=BTC_AMOUNT,
    xmr_amount=XMR_AMOUNT,
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    return xmrto_api.order_check_price(
        btc_amount=btc_amount, xmr_amount=xmr_amount
    )


def order_check_ln_routes(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, ln_invoice=LN_INVOICE,
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    return xmrto_api.order_check_ln_routes(ln_invoice=ln_invoice)


def order_check_parameters(
    xmrto_url=XMRTO_URL, api_version=API_VERSION,
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    return xmrto_api.order_check_parameters()


def generate_qrcode(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, data=QR_DATA
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    qrcode = xmrto_api.generate_qrcode(data=data)
    if not qrcode:
        print("No data provided to convert to qrcode.")
    with open("qrcode.png", "wb") as qrcode_file:
        for chunk in qrcode:
            qrcode_file.write(chunk)
    print("Stored qrcode in qrcode.png.")


def follow_order(order: None, follow=False):
    total = 1
    if order:
        while not order.state == XmrtoOrder.BTC_SENT and not order.error:
            print(order)
            if order.state in (XmrtoOrder.UNPAID, XmrtoOrder.UNDERPAID):
                print("Pay:")
                print(
                    f"    transfer {order.order_status.payment_subaddress} {order.order_status.in_amount_remaining}"
                )
            if not follow:
                return
            if (
                order.state == XmrtoOrder.TIMED_OUT
                or order.state == XmrtoOrder.PURGED
            ):
                total -= 1
                if total == 0:
                    break
            time.sleep(3)
            order.get_order_status()
        print(order)


def logo_action(text=""):
    class customAction(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            print(text)
            setattr(args, self.dest, values)
            sys.exit(0)

    return customAction


def main():
    from ._version import __version__
    from ._logo import __complete__, __xmrto__, __monero__

    parser = argparse.ArgumentParser(
        description=__xmrto__ + "\nInteract with XMR.to.",
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__monero__,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    parser.add_argument(
        "--logo", action=logo_action(text=__complete__), nargs=0,
    )

    config = argparse.ArgumentParser(add_help=False)

    config.add_argument(
        "--url",
        nargs="?",
        default=XMRTO_URL_DEFAULT,
        help="XMR.to url to use.",
    )
    config.add_argument(
        "--api", default=API_VERSION_DEFAULT, help="XMR.to API version to use."
    )

    config.add_argument(
        "--debug", action="store_true", help="Show debug info."
    )
    config.add_argument("--cert", nargs="?", help="Local certificate.")

    # subparsers
    subparsers = parser.add_subparsers(help="Sub commands.", dest="subcommand")
    subparsers.required = True

    # Create order
    create = subparsers.add_parser(
        "create-order",
        parents=[config],
        help="Create an order.",
        description="Create an order.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    create.add_argument(
        "--destination",
        required=True,
        help="Destination (BTC) address to send money to.",
    )
    create_group = create.add_mutually_exclusive_group(required=True)
    btc_group = create_group.add_mutually_exclusive_group()
    btc_group.add_argument("--btc-amount", help="Amount to send in BTC.")
    btc_group.add_argument("--btc", help="Amount to send in BTC.")
    xmr_group = create_group.add_mutually_exclusive_group()
    xmr_group.add_argument("--xmr-amount", help="Amount to send in XMR.")
    xmr_group.add_argument("--xmr", help="Amount to send in XMR.")
    create.add_argument(
        "--follow", action="store_true", help="Keep tracking order."
    )

    # Create lightning order
    create_ln = subparsers.add_parser(
        "create-ln-order",
        parents=[config],
        help="Create a lightning order.",
        description="Create a lightning order.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    create_ln.add_argument(
        "--invoice", required=True, help="Lightning invoice to pay.",
    )
    create_ln.add_argument(
        "--follow", action="store_true", help="Keep tracking order."
    )

    # Track order
    track = subparsers.add_parser(
        "track-order",
        parents=[config],
        help="Track an order.",
        description="Track an order.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    track_group = track.add_mutually_exclusive_group(required=True)
    track_group.add_argument(
        "--secret-key", help="Existing secret key of an existing order."
    )
    track_group.add_argument(
        "--secret", help="Existing secret key of an existing order."
    )
    track_group.add_argument(
        "--key", help="Existing secret key of an existing order."
    )
    track.add_argument(
        "--follow", action="store_true", help="Keep tracking order."
    )

    # Partial payment
    partial = subparsers.add_parser(
        "confirm-partial-payment",
        parents=[config],
        help="Confirm the partial payment of  an order.",
        description="Confirm the partial payment of  an order.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    partial_group = partial.add_mutually_exclusive_group(required=True)
    partial_group.add_argument(
        "--secret-key", help="Existing secret key of an existing order."
    )
    partial_group.add_argument(
        "--secret", help="Existing secret key of an existing order."
    )
    partial_group.add_argument(
        "--key", help="Existing secret key of an existing order."
    )
    partial.add_argument(
        "--follow", action="store_true", help="Keep tracking order."
    )

    # Check price
    price = subparsers.add_parser(
        "check-price",
        parents=[config],
        help="Get price for amount in currency.",
        description="Get price for amount in currency.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    price_group = price.add_mutually_exclusive_group(required=True)
    btc_group = price_group.add_mutually_exclusive_group()
    btc_group.add_argument("--btc-amount", help="Amount to send in BTC.")
    btc_group.add_argument("--btc", help="Amount to send in BTC.")
    xmr_group = price_group.add_mutually_exclusive_group()
    xmr_group.add_argument("--xmr-amount", help="Amount to send in XMR.")
    xmr_group.add_argument("--xmr", help="Amount to send in XMR.")

    # Check ightning routes
    routes = subparsers.add_parser(
        "check-ln-routes",
        parents=[config],
        help="Get available lightning routes.",
        description="Get available lightning routes.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    routes.add_argument(
        "--invoice",
        required=True,
        help="Lightning invoice to check routes for.",
    )

    # Parameters
    parameters = subparsers.add_parser(
        "parameters",
        parents=[config],
        help="Get order parameters.",
        description="Get order parameters.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )

    # Create qrcode
    qrcode = subparsers.add_parser(
        "qrcode",
        parents=[config],
        description="Create a qrcode, is stored in a file called 'qrcode.png'.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=__complete__,
        allow_abbrev=False,
    )
    qrcode.add_argument("--data", required=True, help=".")

    args = parser.parse_args()

    cmd_create_order = False
    cmd_create_ln_order = False
    cmd_track_order = False
    cmd_partial_payment = False
    cmd_check_price = False
    cmd_check_ln_routes = False
    cmd_get_parameters = False
    cmd_create_qrcode = False
    follow = False

    debug = args.debug
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.subcommand == "create-order":
        cmd_create_order = True
        destination_address = args.destination
        btc_amount = args.btc_amount or args.btc
        xmr_amount = args.xmr_amount or args.xmr
        follow = args.follow
    elif args.subcommand == "create-ln-order":
        cmd_create_ln_order = True
        ln_invoice = args.invoice
        follow = args.follow
    elif args.subcommand == "track-order":
        cmd_track_order = True
        secret_key = args.secret_key or args.secret or args.key
        follow = args.follow
    elif args.subcommand == "confirm-partial-payment":
        cmd_partial_payment = True
        secret_key = args.secret_key or args.secret or args.key
        follow = args.follow
    elif args.subcommand == "check-price":
        cmd_check_price = True
        btc_amount = args.btc_amount or args.btc
        xmr_amount = args.xmr_amount or args.xmr
    elif args.subcommand == "check-ln-routes":
        cmd_check_ln_routes = True
        ln_invoice = args.invoice
    elif args.subcommand == "parameters":
        cmd_get_parameters = True
    elif args.subcommand == "qrcode":
        cmd_create_qrcode = True
        qr_data = args.data

    xmrto_url = args.url
    api_version = args.api
    if api_version not in API_VERSIONS_:
        print(f"API {api_version} is not supported.")
        return 1

    global CERTIFICATE
    if not CERTIFICATE:
        CERTIFICATE = args.cert

    if cmd_create_order:
        order = create_order(
            xmrto_url=xmrto_url,
            api_version=api_version,
            out_address=destination_address,
            btc_amount=btc_amount,
            xmr_amount=xmr_amount,
        )

        try:
            follow_order(order=order, follow=follow)
        except KeyboardInterrupt:
            print("\nUser interrupted")
            if order:
                print(order)
    elif cmd_create_ln_order:
        order = create_ln_order(
            xmrto_url=xmrto_url,
            api_version=api_version,
            ln_invoice=ln_invoice,
        )

        try:
            follow_order(order=order, follow=follow)
        except KeyboardInterrupt:
            print("\nUser interrupted")
            if order:
                print(order)
    elif cmd_track_order:
        order_status = track_order(
            xmrto_url=xmrto_url, api_version=api_version, uuid=secret_key
        )

        try:
            follow_order(order=order_status, follow=follow)
        except KeyboardInterrupt:
            print("\nUser interrupted")
            if order_status:
                print(order_status)
    elif cmd_partial_payment:
        order_status = confirm_partial_payment(
            xmrto_url=xmrto_url, api_version=api_version, uuid=secret_key
        )
        try:
            follow_order(order=order_status, follow=follow)
        except KeyboardInterrupt:
            print("\nUser interrupted")
            if order_status:
                print(order_status)
    elif cmd_check_price:
        price, error = order_check_price(
            xmrto_url=xmrto_url,
            api_version=api_version,
            btc_amount=btc_amount,
            xmr_amount=xmr_amount,
        )

        if error:
            print(error)
            return 1

        print(price)
    elif cmd_check_ln_routes:
        routes, error = order_check_ln_routes(
            xmrto_url=xmrto_url,
            api_version=api_version,
            ln_invoice=ln_invoice,
        )

        if error:
            print(error)
            return 1

        print(routes)
    elif cmd_get_parameters:
        parameters, error = order_check_parameters(
            xmrto_url=xmrto_url, api_version=api_version,
        )

        if error:
            print(error)
            return 1

        print(parameters)
    elif cmd_create_qrcode:
        generate_qrcode(
            xmrto_url=xmrto_url, api_version=api_version, data=qr_data
        )


if __name__ == "__main__":
    sys.exit(main())
