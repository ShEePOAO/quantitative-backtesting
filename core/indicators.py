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


def tema(series, n=20):
    n = int(n)
    e1 = series.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    e3 = e2.ewm(span=n, adjust=False).mean()
    return 3 * e1 - 3 * e2 + e3


def kama(series, n=10, fast=2, slow=30):
    n, fast, slow = int(n), int(fast), int(slow)
    change = series.diff(n).abs()
    vol = series.diff().abs().rolling(n).sum()
    er = change / vol.replace(0, np.nan)
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    base = (2 / (slow + 1)) ** 2
    vals = []
    prev = series.iloc[0]
    for i in range(len(series)):
        s = sc.iloc[i]
        if not np.isfinite(s):
            s = base
        prev = prev + s * (series.iloc[i] - prev)
        vals.append(prev)
    return pd.Series(vals, index=series.index)


def linreg(series, n=14):
    n = int(n)
    x = np.arange(n)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()

    def _slope(y):
        return ((x - xm) * (y - y.mean())).sum() / denom

    return series.rolling(n).apply(_slope, raw=True)


def medprice(df):
    return (df["high"] + df["low"]) / 2


def typprice(df):
    return (df["high"] + df["low"] + df["close"]) / 3


def wclprice(df):
    return (df["high"] + df["low"] + 2 * df["close"]) / 4


def midpoint(series, n=14):
    n = int(n)
    return (series.rolling(n).max() + series.rolling(n).min()) / 2


def bias(series, n=20):
    n = int(n)
    m = series.rolling(n).mean()
    return (series - m) / m.replace(0, np.nan) * 100


def dpo(series, n=20):
    n = int(n)
    return series - series.rolling(n).mean().shift(n // 2 + 1)


def cmo(series, n=14):
    n = int(n)
    d = series.diff()
    up = d.clip(lower=0).rolling(n).sum()
    dn = (-d.clip(upper=0)).rolling(n).sum()
    return (up - dn) / (up + dn).replace(0, np.nan) * 100


def bop(df):
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return (df["close"] - df["open"]) / rng


def uo(df, fast=7, mid=14, slow=28):
    fast, mid, slow = int(fast), int(mid), int(slow)
    bp = df["close"] - pd.concat([df["low"], df["close"].shift()], axis=1).min(axis=1)
    tr_ = tr(df)

    def _avg(n):
        return bp.rolling(n).sum() / tr_.rolling(n).sum().replace(0, np.nan)

    return 100 * (4 * _avg(fast) + 2 * _avg(mid) + _avg(slow)) / 7


def tsi(df, long=25, short=13):
    long, short = int(long), int(short)
    m = df["close"].diff()
    num = ema(ema(m, long), short)
    den = ema(ema(m.abs(), long), short)
    return num / den.replace(0, np.nan) * 100


def fi(df, n=13):
    return (df["close"].diff() * df["volume"]).ewm(span=int(n), adjust=False).mean()


def eom(df, n=14):
    n = int(n)
    mid = ((df["high"] + df["low"]) / 2).diff()
    box = (df["volume"] / 1e6) / (df["high"] - df["low"]).replace(0, np.nan)
    return (mid / box).rolling(n).mean()


def supertrend(df, n=10, mult=3.0):
    n = int(n)
    atrv = atr(df, n)
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + mult * atrv
    lower = hl2 - mult * atrv
    close = df["close"]
    fub = upper.to_numpy(dtype=float, copy=True)
    flb = lower.to_numpy(dtype=float, copy=True)
    c = close.to_numpy(dtype=float)
    st = np.full(len(df), np.nan)
    trend = np.ones(len(df), dtype=int)
    for i in range(1, len(df)):
        if np.isfinite(upper.iat[i]):
            if not (upper.iat[i] < fub[i - 1] or c[i - 1] > fub[i - 1]):
                fub[i] = fub[i - 1]
            if not (lower.iat[i] > flb[i - 1] or c[i - 1] < flb[i - 1]):
                flb[i] = flb[i - 1]
            if c[i] > fub[i]:
                trend[i] = 1
            elif c[i] < flb[i]:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]
            st[i] = flb[i] if trend[i] == 1 else fub[i]
    return pd.Series(st, index=df.index), pd.Series(trend, index=df.index)


def psar(df, af=0.02, maxaf=0.2):
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(df)
    out = np.full(n, np.nan)
    if n < 2:
        return pd.Series(out, index=df.index)
    bull = True
    ep = high[0]
    sar = low[0]
    acc = af
    out[0] = sar
    for i in range(1, n):
        sar = sar + acc * (ep - sar)
        if bull:
            if low[i] < sar:
                bull = False
                sar = ep
                ep = low[i]
                acc = af
            else:
                if high[i] > ep:
                    ep = high[i]
                    acc = min(acc + af, maxaf)
                sar = min(sar, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
        else:
            if high[i] > sar:
                bull = True
                sar = ep
                ep = high[i]
                acc = af
            else:
                if low[i] < ep:
                    ep = low[i]
                    acc = min(acc + af, maxaf)
                sar = max(sar, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
        out[i] = sar
    return pd.Series(out, index=df.index)


def keltner(df, n=20, mult=2.0):
    mid = ema(df["close"], int(n))
    r = atr(df, int(n))
    return mid, mid + mult * r, mid - mult * r


def stochrsi(close, n=14, k=3):
    n, k = int(n), int(k)
    r = rsi(close, n)
    ll = r.rolling(n).min()
    hh = r.rolling(n).max()
    s = (r - ll) / (hh - ll).replace(0, np.nan) * 100
    return s.rolling(k).mean()


def pvo(df, fast=12, slow=26, signal=9):
    fast, slow, signal = int(fast), int(slow), int(signal)
    v = df["volume"]
    line = (ema(v, fast) - ema(v, slow)) / ema(v, slow).replace(0, np.nan) * 100
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def nvi(df):
    ret = df["close"].pct_change()
    sign = np.where(ret > 0, 1.0, np.where(ret < 0, 0.0, 1.0))
    return 1000 * (1 + sign * ret).cumprod()


def pvi(df):
    ret = df["close"].pct_change()
    volchg = df["volume"].diff()
    sign = np.where(volchg > 0, 1.0, np.where(volchg < 0, 0.0, 1.0))
    return 1000 * (1 + sign * ret).cumprod()


def rvi(df, n=10):
    n = int(n)
    num = (df["close"] - df["open"]).rolling(n).mean()
    den = (df["high"] - df["low"]).rolling(n).mean()
    return num / den.replace(0, np.nan)


def hh(df, n=20):
    return df["high"].rolling(int(n)).max()


def ll(df, n=20):
    return df["low"].rolling(int(n)).min()


def aroonosc(df, n=25):
    up, dn = aroon(df, n)
    return up - dn

