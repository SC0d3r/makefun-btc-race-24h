import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# Trend-gated long-only dip-buy bot for the make.fun CBBTC 24h bars replay.
#
# One symbol, one position, long only. A round trip costs roughly 19-26 bps in
# fees, modelled slippage and constant-product price impact. The bot buys a
# shallow dip only while the 60-bar trend is up, so it does not fight a falling
# market, then takes a fixed profit, a wide tail stop, or exits on a time limit.
#
# The first two batches send a one-USDC minimum-notional round trip so the
# race window always has at least one filled trade even if the strategy never
# fires. All arithmetic is integer, so the bot is deterministic.

SYMBOL = "CBBTC"
BPS = 10000
MIN_NOTIONAL = 1_000_000  # 1 USDC in quote units

# Entry: close at least DIP_BPS below the high of the last LOOKBACK closes,
# and close at or above its level TREND_LOOKBACK bars ago (the trend is up).
LOOKBACK = 60
DIP_BPS = 50
TREND_LOOKBACK = 60

# Exit: +TAKE_BPS over the entry close, a -STOP_BPS stop as tail insurance, or
# MAX_HOLD_BARS bars, whichever comes first.
TAKE_BPS = 80
STOP_BPS = 300
MAX_HOLD_BARS = 480

# Spend all cash on one entry.
MAX_SLIPPAGE_BPS = 10000

_closes = []
_entry_price = 0
_entry_seq = -1
# The one-USDC probe: 0 = still to buy, 1 = bought and still to sell, 2 = done.
_compliance = 0


def _buy(state, notional):
    notional = min(notional, state.cash, state.weight_room(SYMBOL))
    if notional < MIN_NOTIONAL:
        return None
    return {
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": notional,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def _sell(held):
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": held.qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def on_batch(state, batch):
    global _entry_price, _entry_seq, _compliance

    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
    if bar is not None:
        _closes.append(int(bar["c"]))

    seq = batch["seq"]
    held = state.positions.get(SYMBOL)

    # The one-USDC probe: buy it on the first batch that has a bar, sell it as
    # soon as it fills, and retry either leg if the market refuses it.
    if _compliance < 2:
        if _compliance == 0:
            if held is not None:
                _compliance = 1
            elif bar is not None:
                order = _buy(state, MIN_NOTIONAL)
                return [order] if order is not None else []
            else:
                return []
        if _compliance == 1:
            if held is None:
                _compliance = 2
            else:
                return [_sell(held)]

    if held is not None:
        if _entry_seq < 0:
            _entry_seq = seq
        close = state.close(SYMBOL)
        take = close * BPS >= _entry_price * (BPS + TAKE_BPS)
        stop = close * BPS <= _entry_price * (BPS - STOP_BPS)
        old = seq - _entry_seq >= MAX_HOLD_BARS
        if take or stop or old:
            return [_sell(held)]
        return []

    _entry_seq = -1
    # Wait for a full lookback so the peak and the trend reference are real.
    if len(_closes) > LOOKBACK and len(_closes) > TREND_LOOKBACK:
        close = _closes[-1]
        peak = max(_closes[-LOOKBACK:])
        trend_ok = close >= _closes[-1 - TREND_LOOKBACK]
        if close * BPS <= peak * (BPS - DIP_BPS) and trend_ok:
            order = _buy(state, state.cash)
            if order is not None:
                _entry_price = close
                _entry_seq = seq
                return [order]
    return []


def main():
    makefun_bars.run(on_batch)


if __name__ == "__main__":
    main()
