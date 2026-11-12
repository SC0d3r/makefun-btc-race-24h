# makefun-btc-race-24h

A long-only Python bot for make.fun's `agent-fun/bars-replay/v1` replay of
CBBTC/USDC one-minute bars.

## Strategy

A round trip costs roughly 19-26 bps in fees, modelled slippage and
constant-product price impact. The bot buys a shallow dip only while the
60-bar trend is up:

- the close is at least 50 bps below the highest close of the last 60 bars, and
- the close is at or above its level 60 bars ago.

It exits at +80 bps over the entry close, at a -300 bps tail stop, or after
480 bars. A one-USDC minimum-notional probe on the first two batches
guarantees at least one own filled trade on any window.

The bot is deterministic: no clock, no network, no randomness, integer
arithmetic only.

## Layout

- `main.py` - entrypoint and strategy
- `vendor/makefun_bars.py` - the kit's Python SDK shim
- `LICENSE` - MIT
- `.makefun/owner.json` - the entry wallet

## Run

The grader runs `python3 -P -s /bot/main.py` with the repository mounted at
`/bot`. Locally, `python3 main.py` reads the protocol hello, the bar batches
and the orders replies on stdin and stdout.
