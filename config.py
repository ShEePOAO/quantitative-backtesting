ASSETS = {
    "BTC": {"binance": "BTCUSDT", "label": "比特幣"},
    "ETH": {"binance": "ETHUSDT", "label": "以太坊"},
    "XRP": {"binance": "XRPUSDT", "label": "瑞波幣"},
    "BNB": {"binance": "BNBUSDT", "label": "幣安幣"},
    "SOL": {"binance": "SOLUSDT", "label": "Solana"},
    "DOGE": {"binance": "DOGEUSDT", "label": "狗狗幣"},
    "ADA": {"binance": "ADAUSDT", "label": "艾達幣"},
    "AVAX": {"binance": "AVAXUSDT", "label": "Avalanche"},
    "BCH": {"binance": "BCHUSDT", "label": "比特幣現金"},
    "DOT": {"binance": "DOTUSDT", "label": "Polkadot"},
    "LINK": {"binance": "LINKUSDT", "label": "Chainlink"},
    "LTC": {"binance": "LTCUSDT", "label": "萊特幣"},
    "POL": {"binance": "POLUSDT", "label": "Polygon"},
    "SHIB": {"binance": "SHIBUSDT", "label": "柴犬幣"},
    "TRX": {"binance": "TRXUSDT", "label": "波場"},
    "XLM": {"binance": "XLMUSDT", "label": "恆星幣"},
    # --- 股票（Serenity @aleabitoreddit 提及量 Top 10；來源 data\\import_csv\\<SYM>.csv，日線）---
    "NBIS": {"binance": "NBIS", "label": "Nebius"},
    "SIVE": {"binance": "SIVE", "label": "Sivers (SIVE.ST)"},
    "NVDA": {"binance": "NVDA", "label": "Nvidia"},
    "LITE": {"binance": "LITE", "label": "Lumentum"},
    "AXTI": {"binance": "AXTI", "label": "AXT"},
    "AAOI": {"binance": "AAOI", "label": "Applied Optoelectronics"},
    "IREN": {"binance": "IREN", "label": "IREN"},
    "GOOGL": {"binance": "GOOGL", "label": "Alphabet"},
    "MSFT": {"binance": "MSFT", "label": "Microsoft"},
    "META": {"binance": "META", "label": "Meta"},
    "COIN": {"binance": "COIN", "label": "Coinbase"},
    "CRCL": {"binance": "CRCL", "label": "Circle"},
    "MSTR": {"binance": "MSTR", "label": "MicroStrategy"},
    "RIOT": {"binance": "RIOT", "label": "Riot"},
}

# 股票資產（日線長歷史 + 1h 原始資料；可產生 1h/4h/6h/12h 與 1d/1w）
STOCK_SYMBOLS = {"NBIS", "SIVE", "NVDA", "LITE", "AXTI", "AAOI", "IREN", "GOOGL", "MSFT", "META",
                 "COIN", "CRCL", "MSTR", "RIOT"}
STOCK_INTERVALS = ["1h", "4h", "6h", "12h", "1d", "1w"]

INTERVALS = {
    "5m": "5 分鐘", "15m": "15 分鐘", "30m": "30 分鐘",
    "1h": "1 小時", "4h": "4 小時", "6h": "6 小時", "12h": "12 小時",
    "1d": "日線", "1w": "週線",
}

PERIODS_PER_YEAR = {"5m": 105120, "15m": 35040, "30m": 17520, "1h": 8760, "4h": 2190, "6h": 1460, "12h": 730, "1d": 365, "1w": 52}

DEFAULT_LOOKBACK_DAYS = {"5m": 30, "15m": 90, "30m": 180, "1h": 180, "4h": 540, "6h": 720, "12h": 900, "1d": 1095, "1w": 2190}
