# Quant Studio

量化回測 — 在瀏覽器用 Python 寫交易策略並回測。這是另一套量化回測軟體「自訂策略」頁的**獨立重寫版**：只保留自訂策略那一頁的功能。

## 架構

```
quant-studio\
├── server.py          # FastAPI 後端：靜態檔 + /api/*
├── engine.py          # 回測引擎：執行策略、回測、多幣組合、look-ahead、策略檔管理
├── config.py          # 資產 / 週期 / periods_per_year（複製自原版）
├── core\              # 回測核心（backtest / hedge / indicators / metrics，複製自原版）
├── data\fetcher.py    # 資料獲取：讀取本機 CSV（`QUANT_IMPORT_DIR`）、自有 data\cache
├── user_strategies\   # 使用者策略 .py
├── docs\使用手冊.md    # 對應使用手冊
├── web\               # 純 HTML/CSS/JS 前端
│   ├── index.html
│   ├── vendor\galaxy.min.js   # GalaxyJS（動畫層，MIT，vendored）
│   └── assets\{styles.css, app.js}
├── PRODUCT.md / DESIGN.md
└── requirements.txt
```

## 執行

```powershell
cd C:\quant-studio
pip install -r requirements.txt
python server.py
# 瀏覽器打開 http://127.0.0.1:8050
```

## 功能

- 以 Python 撰寫 `generate(df, params)` 回傳目標倉位（0 / 1 / -1）
- `PARAM_DEFS` 自動生成參數輸入
- 引擎自動路由：做多 / 多空（含 -1）/ 網格鎖倉（勾選）
- 回測設定：資金、手續費、滑點、倉位、槓桿、波動目標、止損止盈、倉位管理（逆馬丁 / 馬丁）
- 未來函數（look-ahead）截斷檢測
- 多幣等權 / 加權組合回測
- 策略檔案存讀（`user_strategies\*.py`）
- 對應使用手冊（頁內渲染）
- 動畫/互動層：GalaxyJS（空狀態宇宙視窗、masthead 微光、`Galaxy.confirm`），尊重 `prefers-reduced-motion`

## 未來計劃

- **實盤交易對接**：讓同一份 `generate(df, params)` 策略除回測外也能（先 dry-run / Testnet）下單；目標為 **USDT-M 合約（可做空 / 槓桿）**。回測與實盤共用策略碼，差異只在執行層與資料來源。

## 資料

- 需自備行情 CSV：放到 `data\import_csv\<SYMBOL>.csv`，或以環境變數 `QUANT_IMPORT_DIR` 指向既有資料夾。
- 格式：`DateTime,Open,High,Low,Close,Volume`（分鐘或日線皆可，程式會重採樣）。
- 快取寫在本專案 `data\cache`（已 gitignore，會自動重建）。
