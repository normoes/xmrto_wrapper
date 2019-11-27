# XMR.to wrapper


## Goal:
Interact with XMR.to.

## How to:
* General usage
  - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
  - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --xmr-amount 1`
  - `python xmrto_wrapper.py track-order --secret-key xmrto-ebmA9q`
  - `python xmrto_wrapper.py create-and-track-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
  - `python xmrto_wrapper.py create-and-track-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --xmr-amount 1`
  - `python xmrto_wrapper.py confirm-partial-payment --secret-key xmrto-ebmA9q`
  - `python xmrto_wrapper.py price --btc-amount 0.01`
* Get help
  - `xmrto_wrapper.py -h`
* You can
  - Create an order: `python xmrto_wrapper.py create-order --destination ... --btc-amount|--xmr-amount ...`
  - Track an order: `python xmrto_wrapper.py track-order --secret-key ...`
  - Create and track an order: `python xmrto_wrapper.py create-and-track-order --destination ... --btc-amount|--xmr-amount ...`
  - Confirm a partial payment (of an underpaid order): `python xmrto_wrapper.py confirm-partial-payment --secret-key ...`
  - Get a recent price: `python xmrto_wrapper.py price --btc-amount|--xmr-amount`
* The API used is `--api v2` by default, so no need to actually set that parameter.
* The URL used is `--url https://xmr.to` by default, so no need to actually set that parameter.

When called as python script `python xmrto_wrapper.py` configure it using cli options.

See:
* `python xmrto_wrapper.py --help`.
* `python xmrto_wrapper.py create-order --help`

When importing as module `import xmrto_wrapper` environment variables are considered:
* `XMRTO_URL`
* `API_VERSION`
* `DESTINATION_ADDRESS`
* `BTC_AMOUNT`
* `XMR_AMOUNT`
* `SECRET_KEY`

## Use as module:
`test.py` shows how to import as module.

## Executable
If installed using `pip` (from github), a system executable will be installed as well.
This way, you can just use the tool as every executable on your system.
```
xmrto_wrapper --help
```

*Note*:
There will be a pypi package very soon.
