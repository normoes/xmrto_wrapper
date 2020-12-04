[![GitHub Release](https://img.shields.io/github/v/release/monero-ecosystem/xmrto_wrapper.svg)](https://github.com/monero-ecosystem/xmrto_wrapper/releases)
[![GitHub Tags](https://img.shields.io/github/v/tag/monero-ecosystem/xmrto_wrapper.svg)](https://github.com/monero-ecosystem/xmrto_wrapper/tags)

# XMR.to wrapper

Interact with XMR.to.

This is built according to the XMR.to [API documentation](https://xmrto-api.readthedocs.io/en/latest/).

With `https://test.xmr.to` you can pay testnet BTC with stagenet XMR (including lightning payments).

## How to
* Get help
  - `xmrto_wrapper -h`
* General usage
  - Create an order for an amount in `BTC`:
      ```
          # Create an order for 0.001 BTC:
          xmrto_wrapper create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001
          # Result:
          {"uuid": "xmrto-p4XtrP", "state": "TO_BE_CREATED", "btc_dest_address": "3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY", "btc_amount": "0.001", "uses_lightning": false}
          # If XMR.to is fast enough with the order processing, the result can also be:
          {"uuid": "xmrto-LAYDkk", "state": "UNPAID", "btc_dest_address": "3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY", "btc_amount": "0.001", "uses_lightning": false, "receiving_subaddress": "86hZP8Qddg2KXyvjLPTRs9a7C5zwAgC21RcwGtEjD3RPCzfbu4aKBeYgqFgpcsNNCcP5iGuswbMKRFXLHiSu45sWMuRYrxc", "incoming_amount_total": "0.1373", "remaining_amount_incoming": "0.1373", "incoming_price_btc": "0.00728332", "btc_amount_partial": "0", "seconds_till_timeout": 2697, "created_at": "2020-05-01T18:47:57Z"}
      ```
      + `--btc` is the equivalent of `--btc-amount` and can be used interchangeably.
      + It's possible to give the amount in `XMR`, where `--xmr` is the equivalent of `--xmr-amount` (They can be used interchangeably).
          ```
              # Create an order for 1 XMR:
              xmrto_wrapper create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --xmr-amount 1
              # Result:
              {"uuid": "xmrto-JSSqo3", "state": "TO_BE_CREATED", "btc_dest_address": "3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY", "btc_amount": "0.00722172", "uses_lightning": false}
          ```
      + Use `--follow` to keep tracking the order.
      + Prior to `v0.1` there used to be a separate sub command: `--create-and-track-order`. `--follow` provides the same behaviour.
  - Track an existing order:
      ```
          xmrto_wrapper track-order --secret-key xmrto-ebmA9q
      ```
      + `--secret` and `--key` are the equivalents of `--secret-key` and can be used interchangeably.
      + Use `--follow` to keep tracking the order.
  - Confirm an underpaid order (for an underpaid order):
      ```
          xmrto_wrapper confirm-partial-payment --secret-key xmrto-ebmA9q
      ```
      + `--secret` and `--key` are the equivalents of `--secret-key` and can be used interchangeably.
      + Use `--follow` to keep tracking the order.
  - Get the recent price for an amount in `BTC`:
      ```
          xmrto_wrapper check-price --btc-amount 0.01
      ```
      + `--btc` is the equivalent of `--btc-amount` and can be used interchangeably.
      + It's possible to give the amount in `XMR`, where `--xmr` is the equivalent of `--xmr-amount` (They can be used interchangeably).
          ```
               xmrto_wrapper check-price --xmr-amount 1
          ```
      + Use `--follow` to keep tracking the order.
* The API used is `--api v3` by default, so no need to actually set that parameter.
* The URL used is `--url https://xmr.to` by default, so no need to actually set that parameter.
    - There also is `--url https://test.xmr.to` for stagenet XMR.
    - Often `https://test.xmr.to` has some new features available for testing.
* More info
  - `xmrto_wrapper.py --version`
  - `xmrto_wrapper.py --logo`
* The option `--debug` shows debug information.

See:
* `xmrto_wrapper --help`.
* `xmrto_wrapper create-order --help`
* ...

When importing as module `from xmrto_wrapper import xmrto_wrapper` environment variables are considered:

| cli option      | environment variable  |
|-----------------|-----------------------|
| `--url`         | `XMRTO_URL`           |
| `--api`         | `API_VERSION`         |
| `--destination` | `DESTINATION_ADDRESS` |
| `--btc-amount`,<br>`--btc`  | `BTC_AMOUNT`          |
| `--xmr-amount`,<br>`--xmr`  | `XMR_AMOUNT`          |
| `--secret-key`,<br>`--secret`,<br>`--key`  | `SECRET_KEY`          |
| `--invoice`     | `LN_INVOICE`          |

## requirements.txt vs. setup.py

According to these sources:
* [python documentation](https://packaging.python.org/discussions/install-requires-vs-requirements/)
* [stackoverflow - second answer by jonathan Hanson](https://stackoverflow.com/questions/14399534/reference-requirements-txt-for-the-install-requires-kwarg-in-setuptools-setup-py)

I try to stick to:
* `requirements.txt` lists the necessary packages to make a deployment work.
* `setup.py` declares the loosest possible dependency versions.

### Creating `requirements.txt`

You won't ever need this probably - This is helpful when developing.

`pip-tools` is used to create `requirements.txt`.
* There is `requirements.in` where dependencies are set and pinned.
* To create the `requirements.txt`, run `update_requirements.sh` which basically just calls `pip-compile`.

**_Note_**:
* There also is `build_requirements.txt` which only contains `pip-tools`. I found, when working with virtual environments, it is necessary to install `pip-tools` inside the virtual environment as well. Otherwise `pip-sync` would install outside the virtual environment.

A development environment can be created like this:
```bash
    # Create a virtual environment 'venv'.
    python -m venv venv
    # Activate the virtual environment 'venv'.
    . /venv/bin/activate
    # Install 'pip-tools'.
    pip install --upgrade -r build_requirements.txt
    # Install dependencies.
    pip-sync requirements.txt
    ...
    python -m xmrto_wrapper.xmrto_wrapper create-order --url https://test.xmr.to --api v3 --destination="tb1qkw6npn7ann5nw9f7l94qkqhh8pdtnsuxlw3v8q" --btc 0.5 --follow
    ...
    # Deactivate the virtual environment 'venv'.
    deactivate
```

## Use as module
`module_example.py` shows how to import as module.

## Executable
If installed using `pip`, a system executable will be installed as well.
This way, you can just use the tool like every executable on your system.
```
xmrto_wrapper --help
```

---

If you would like to donate - Thanks:

`86Avv8siJc1fG85FmNaUNK4iGMXUHLGBY2QwR3zybFMELXrNA34ioEahrupu16v6mZb2hqp2f89YH78oTvyKaha4QRVk2Rb`
