import numpy as np
import pandas as pd

TRADE_COLUMNS = ["進場時間", "進場價", "出場時間", "出場價", "數量", "成本", "收入", "盈虧", "收益率", "原因"]


def compute_metrics(equity, trades, periods_per_year=365, exposure=0.0, buy_hold_return=0.0):
    eq = equity.dropna()
    if len(eq) < 2:
        return {}
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1)
    ppy = float(periods_per_year)
    years = len(eq) / ppy
    idx = getattr(eq, "index", None)
    if isinstance(idx, pd.DatetimeIndex) and len(eq) >= 2:
        span_years = (idx[-1] - idx[0]).total_seconds() / (365.25 * 86400.0)
        if span_years > 0:
            years = span_years
            ppy = len(eq) / span_years
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) if years > 0 and eq.iloc[0] > 0 else 0.0
    dd = eq / eq.cummax() - 1
    max_dd = float(dd.min())
    rets = eq.pct_change().dropna()
    std = rets.std()
    ann = np.sqrt(ppy)
    sharpe = float(rets.mean() / std * ann) if std and std > 0 else 0.0
    downside = rets[rets < 0].std()
    sortino = float(rets.mean() / downside * ann) if downside and downside > 0 else 0.0
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0

    closed = trades[trades["出場時間"].notna()] if len(trades) else trades
    n_trades = len(closed)
    if n_trades > 0:
        pnl = closed["盈虧"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        win_rate = float(len(wins) / n_trades)
        gross_win = float(wins.sum())
        gross_loss = float(-losses.sum())
        profit_factor = gross_win / gross_loss if gross_loss > 0 else (np.inf if gross_win > 0 else 0.0)
        avg_trade = float(pnl.mean())
        avg_win = float(wins.mean()) if len(wins) else 0.0
        avg_loss = float(losses.mean()) if len(losses) else 0.0
        best_trade = float(pnl.max())
        worst_trade = float(pnl.min())
    else:
        win_rate = 0.0
        profit_factor = 0.0
        avg_trade = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        best_trade = 0.0
        worst_trade = 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade": avg_trade,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "exposure": float(exposure),
        "buy_hold_return": float(buy_hold_return),
        "excess_return": total_return - float(buy_hold_return),
    }
