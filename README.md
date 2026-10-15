# Quant Studio

> **不會開啟／執行這個程式？直接問 AI 就對了。**
> 把這個專案交給 AI，並描述你的問題（例如「這是什麼？我要怎麼在我的電腦上把它跑起來？」），它會一步步帶你安裝與啟動。想改功能、寫策略也可以一併問。建議搭配 **DeepSeek API**，成本較低。
>
> **Don't know how to run it? Just ask an AI.**
> Hand this project to an AI and describe your problem (e.g. "what is this? how do I run it on my computer?") — it will walk you through installing and launching step by step. You can also ask it to add features or write strategies. **DeepSeek API** recommended (cheaper).

A browser-based quant **backtesting workbench**. Write trading strategies in Python, run honest backtests, and inspect performance, equity, drawdown, trades and per-asset stats. Standalone rewrite of the "custom strategy" page of another backtesting tool.

**[English](#english) · [繁體中文](#繁體中文)**

---

## English

### Features

- Write `generate(df, params)` returning target positions (`0` flat / `1` long / `-1` short)
- Optional `PARAM_DEFS` → auto-generated parameter inputs
- Engine auto-routing: long-only · long/short (when `-1` present) · grid-hedge (opt-in)
- Backtest settings: capital, fees, slippage, base position, leverage, volatility targeting, stop-loss / take-profit, position sizing (fixed / anti-martingale / martingale)
- Look-ahead detection (truncation re-test)
- Multi-asset equal-weight / weighted portfolio backtest
- Strategy file save/load (`user_strategies/*.py`)
- Built-in manual rendered in-app
- Bilingual UI (繁體中文 / English)

### Architecture

```
quant-studio/
├── server.py           # FastAPI backend: static files + /api/*
├── engine.py           # Backtest engine: run strategy, backtest, multi-asset portfolio, look-ahead, strategy files
├── config.py           # Assets / intervals / periods_per_year
├── core/               # Backtest core (backtest / hedge / indicators / metrics)
├── data/fetcher.py     # Data: read local CSV (QUANT_IMPORT_DIR) + own data/cache
├── user_strategies/    # User strategies (*.py, gitignored)
├── docs/使用手冊.md     # In-app manual (Chinese)
├── web/                # Vanilla HTML/CSS/JS frontend
│   ├── index.html
│   ├── vendor/galaxy.min.js   # GalaxyJS (animation layer, MIT, vendored)
│   └── assets/{styles.css, app.js, i18n.js}
├── PRODUCT.md / DESIGN.md
├── update_stocks.py
└── requirements.txt
```

### Run

```bash
cd quant-studio
pip install -r requirements.txt
python server.py
# open http://127.0.0.1:8050
```

On Windows you can also double-click `start.bat`.

> **Get the code with `git clone`** (not a ZIP download) — then the start screen has a **Check for updates** button that pulls the latest version from GitHub in one click.

### Data

- A small set of **daily historical data** is bundled in `data/cache/`: BTC, ETH, SOL, XRP, BNB (plus 12h for BTC/SOL) and NVDA, GOOGL, COIN. Clone it and run with **Local CSV + Daily** to try it right away.
- Also bundled in `data/import_csv/` (**daily + hourly**) for 12 common stocks: `2330 0050 2317 2454 2308 2303` (Taiwan) and `AAPL AMZN TSLA AMD TSM AVGO` (US) — so they work out of the box at 1h/4h/6h/12h/1d/1w.
- Provide your own market CSV: `data/import_csv/<SYMBOL>.csv`, or point `QUANT_IMPORT_DIR` at an existing folder.
- **Stocks (Taiwan + US)**: run `python update_stocks.py` (yfinance) to fetch **daily + hourly** into your import dir. It covers common TW names (2330 TSMC, 0050, 2317, 2454, …) and US names (AAPL, MSFT, NVDA, TSLA, TSM, …); `python update_stocks.py 2330 TSLA` updates only those. `python update_stocks.py --list` lists all.
- Format: `DateTime,Open,High,Low,Close,Volume` (intraday or daily; the app resamples as needed).
- Other intervals are derived from the source CSV and cached into `data/cache` (`<SYMBOL>_<interval>_import.csv`).
- Note: bundled market data is for research/demo only — check the data provider's redistribution terms before reuse.

### Roadmap

- **Live trading**: run the same `generate(df, params)` strategy beyond backtests (dry-run / Testnet first), targeting **USDT-M futures** (short & leverage). Backtest and live share the strategy code; only the execution layer and data source differ.

### License

MIT — see [LICENSE](LICENSE).

---

## 繁體中文

### 功能

- 以 Python 撰寫 `generate(df, params)`，回傳目標倉位（`0` 空倉 / `1` 做多 / `-1` 做空）
- 可選 `PARAM_DEFS` → 自動生成參數輸入
- 引擎自動路由：做多 · 多空（含 `-1`）· 網格鎖倉（可勾選）
- 回測設定：資金、手續費、滑點、基礎倉位、槓桿、波動目標、止損止盈、倉位管理（固定 / 逆馬丁 / 馬丁）
- 未來函數（look-ahead）截斷檢測
- 多資產等權 / 加權組合回測
- 策略檔案存讀（`user_strategies/*.py`）
- 內建使用手冊（頁內渲染）
- 介面支援中英文切換（繁體中文 / English）

### 架構

```
quant-studio/
├── server.py           # FastAPI 後端：靜態檔 + /api/*
├── engine.py           # 回測引擎：執行策略、回測、多資產組合、look-ahead、策略檔管理
├── config.py           # 資產 / 週期 / periods_per_year
├── core/               # 回測核心（backtest / hedge / indicators / metrics）
├── data/fetcher.py     # 資料獲取：讀取本機 CSV（QUANT_IMPORT_DIR）、自有 data/cache
├── user_strategies/    # 使用者策略（*.py，已 gitignore）
├── docs/使用手冊.md     # 使用手冊（頁內渲染）
├── web/                # 純 HTML/CSS/JS 前端
│   ├── index.html
│   ├── vendor/galaxy.min.js   # GalaxyJS（動畫層，MIT，vendored）
│   └── assets/{styles.css, app.js, i18n.js}
├── PRODUCT.md / DESIGN.md
├── update_stocks.py
└── requirements.txt
```

### 執行

```bash
cd quant-studio
pip install -r requirements.txt
python server.py
# 瀏覽器打開 http://127.0.0.1:8050
```

Windows 也可直接雙擊 `start.bat`。

> 建議用 **`git clone`** 下載（而非 ZIP）；這樣初始畫面就會有 **「檢查更新」** 按鈕，一鍵把專案更新到 GitHub 最新版。

### 資料

- 附帶一批**日線歷史資料**（在 `data/cache/`）：BTC、ETH、SOL、XRP、BNB（另有 BTC/SOL 的 12h）與 NVDA、GOOGL、COIN。clone 後選「本地 CSV ＋ 日線」即可直接回測。
- 另附 12 檔常見股票的**日線＋小時**資料（在 `data/import_csv/`）：台股 `2330 0050 2317 2454 2308 2303`、美股 `AAPL AMZN TSLA AMD TSM AVGO`——clone 後 1h/4h/6h/12h/1d/1w 都能直接跑。
- 也可自備行情 CSV：放到 `data/import_csv/<SYMBOL>.csv`，或以環境變數 `QUANT_IMPORT_DIR` 指向既有資料夾。
- **股票（台股＋美股）**：執行 `python update_stocks.py`（yfinance）會抓**日線＋小時**到你指定的資料夾。涵蓋常見台股（2330 台積電、0050、2317、2454…）與美股（AAPL、MSFT、NVDA、TSLA、TSM…）；`python update_stocks.py 2330 TSLA` 只更新指定幾檔、`--list` 列出全部。
- 格式：`DateTime,Open,High,Low,Close,Volume`（分鐘或日線皆可，程式會視需要重採樣）。
- 其他週期由來源 CSV 重採樣後快取到 `data/cache`（`<SYMBOL>_<interval>_import.csv`）。
- 注意：附帶的行情資料僅供研究／示範，重複散布前請自行確認資料來源的授權條款。

### 未來計劃

- **實盤交易對接**：讓同一份 `generate(df, params)` 策略除回測外也能（先 dry-run / Testnet）下單，目標為 **USDT-M 合約（可做空 / 槓桿）**。回測與實盤共用策略碼，差異只在執行層與資料來源。

### 授權

MIT，詳見 [LICENSE](LICENSE)。
