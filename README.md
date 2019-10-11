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

When called as python script `python xmrto_wrapper.py` configure it using cli options.

When importing as module `import xmrto_wrapper` environment variables are considered.

##
`test.py` shows how to import as module.
