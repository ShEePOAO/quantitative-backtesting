# Quant Studio

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

### Data

- Provide your own market CSV: `data/import_csv/<SYMBOL>.csv`, or point `QUANT_IMPORT_DIR` at an existing folder.
- Format: `DateTime,Open,High,Low,Close,Volume` (intraday or daily; the app resamples as needed).
- Cache is written to `data/cache` (gitignored, regenerated automatically).

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

### 資料

- 需自備行情 CSV：放到 `data/import_csv/<SYMBOL>.csv`，或以環境變數 `QUANT_IMPORT_DIR` 指向既有資料夾。
- 格式：`DateTime,Open,High,Low,Close,Volume`（分鐘或日線皆可，程式會視需要重採樣）。
- 快取寫在 `data/cache`（已 gitignore，會自動重建）。

### 未來計劃

- **實盤交易對接**：讓同一份 `generate(df, params)` 策略除回測外也能（先 dry-run / Testnet）下單，目標為 **USDT-M 合約（可做空 / 槓桿）**。回測與實盤共用策略碼，差異只在執行層與資料來源。

### 授權

MIT，詳見 [LICENSE](LICENSE)。
