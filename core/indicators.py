import numpy as np
import pandas as pd


def sma(series, n=20):
    return series.rolling(int(n)).mean()


def ema(series, n=20):
    return series.ewm(span=int(n), adjust=False).mean()


def wma(series, n=20):
    n = int(n)
    w = np.arange(1, n + 1)
    return series.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def rma(series, n=14):
    return series.ewm(alpha=1.0 / int(n), adjust=False).mean()


def dema(series, n=20):
    n = int(n)
    e1 = series.ewm(span=n, adjust=False).mean()
    return 2 * e1 - e1.ewm(span=n, adjust=False).mean()


def hma(series, n=20):
    n = int(n)
    half = max(1, n // 2)
    sq = max(1, int(np.sqrt(n)))

    def _w(s, m):
        w = np.arange(1, m + 1)
        return s.rolling(m).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)

    return _w(2 * _w(series, half) - _w(series, n), sq)


def stdev(series, n=20):
    return series.rolling(int(n)).std(ddof=0)


def zscore(series, n=20):
    n = int(n)
    m = series.rolling(n).mean()
    s = series.rolling(n).std(ddof=0)
    return (series - m) / s.replace(0, np.nan)


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def roc(close, n=20):
    return close.pct_change(int(n)) * 100


def mom(series, n=10):
    return series.diff(int(n))


def trix(close, n=15):
    n = int(n)
    e1 = close.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    e3 = e2.ewm(span=n, adjust=False).mean()
    return e3.pct_change() * 100


def macd(close, fast=12, slow=26, signal=9):
    fast, slow, signal = int(fast), int(slow), int(signal)
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def ppo(df, fast=12, slow=26, signal=9):
    fast, slow, signal = int(fast), int(slow), int(signal)
    close = df["close"]
    f = close.ewm(span=fast, adjust=False).mean()
    s = close.ewm(span=slow, adjust=False).mean()
    line = (f - s) / s.replace(0, np.nan) * 100
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def bollinger(close, n=20, k=2.0):
    mid = close.rolling(int(n)).mean()
    std = close.rolling(int(n)).std(ddof=0)
    return mid, mid + k * std, mid - k * std


def tr(df):
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)


def atr(df, n=14):
    return tr(df).ewm(alpha=1.0 / int(n), adjust=False).mean()


def natr(df, n=14):
    return atr(df, n) / df["close"].replace(0, np.nan) * 100


def _dm(df):
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    return pd.Series(plus, index=df.index), pd.Series(minus, index=df.index)


def dmi(df, n=14):
    n = int(n)
    tr_ = tr(df).ewm(alpha=1.0 / n, adjust=False).mean()
    plus_dm, minus_dm = _dm(df)
    pdi = 100 * plus_dm.ewm(alpha=1.0 / n, adjust=False).mean() / tr_.replace(0, np.nan)
    mdi = 100 * minus_dm.ewm(alpha=1.0 / n, adjust=False).mean() / tr_.replace(0, np.nan)
    return pdi, mdi


def adx(df, n=14):
    n = int(n)
    pdi, mdi = dmi(df, n)
    dx = (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan) * 100
    return dx.ewm(alpha=1.0 / n, adjust=False).mean()


def cci(df, n=20):
    n = int(n)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = tp.rolling(n).mean()
    md = (tp - ma).abs().rolling(n).mean()
    return (tp - ma) / (0.015 * md.replace(0, np.nan))


def mfi(df, n=14):
    n = int(n)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    rmf = tp * df["volume"]
    delta = tp.diff()
    pos = rmf.where(delta > 0, 0.0).rolling(n).sum()
    neg = rmf.where(delta < 0, 0.0).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))


def willr(df, n=14):
    n = int(n)
    hh = df["high"].rolling(n).max()
    ll = df["low"].rolling(n).min()
    return (hh - df["close"]) / (hh - ll).replace(0, np.nan) * -100


def obv(df):
    direction = np.sign(df["close"].diff()).fillna(0.0)
    return (direction * df["volume"]).cumsum()


def vwap(df, n=20):
    n = int(n)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum().replace(0, np.nan)


def vwma(df, n=20):
    n = int(n)
    return (df["close"] * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum().replace(0, np.nan)


def cmf(df, n=20):
    n = int(n)
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng
    return (mfm * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum().replace(0, np.nan)


def kdj(df, n=9, m1=3, m2=3):
    n, m1, m2 = int(n), int(m1), int(m2)
    ll = df["low"].rolling(n).min()
    hh = df["high"].rolling(n).max()
    rsv = (df["close"] - ll) / (hh - ll).replace(0, np.nan) * 100
    k = rsv.ewm(alpha=1.0 / m1, adjust=False).mean()
    d = k.ewm(alpha=1.0 / m2, adjust=False).mean()
    return k, d, 3 * k - 2 * d


def stoch(df, n=14, m1=3, m2=3):
    return kdj(df, n, m1, m2)


def aroon(df, n=25):
    n = int(n)
    up = df["high"].rolling(n + 1).apply(lambda x: 100 * x.argmax() / n, raw=True)
    dn = df["low"].rolling(n + 1).apply(lambda x: 100 * x.argmin() / n, raw=True)
    return up, dn


def donchian(df, n=20):
    n = int(n)
    up = df["high"].rolling(n).max()
    lo = df["low"].rolling(n).min()
    return up, (up + lo) / 2, lo


def ao(df, fast=5, slow=34):
    fast, slow = int(fast), int(slow)
    med = (df["high"] + df["low"]) / 2
    return med.rolling(fast).mean() - med.rolling(slow).mean()
