"use strict";
(function () {
  const EN = {
    "執行回測": "Run backtest",
    "開始優化": "Run optimize",
    "回測結果": "Results",
    "參數優化": "Optimize",
    "使用手冊": "Manual",
    "量化回測": "Quant Backtest",
    "策略台": "Strategy",
    "讀數區": "Readouts",
    "資產與區間": "Asset & range",
    "資料來源": "Data source",
    "時間週期": "Interval",
    "回測區間": "Backtest range",
    "快速區間": "Quick range",
    "起始日期": "Start date",
    "結束日期": "End date",
    "回測設定": "Backtest settings",
    "回測模式": "Mode",
    "單一資產": "Single asset",
    "多籌組合": "Multi-asset",
    "手續費率": "Fee rate",
    "滑點": "Slippage",
    "基礎倉位": "Base position",
    "倉位管理（逆馬丁 / 馬丁）": "Position sizing (anti-martingale / martingale)",
    "固定倉位": "Fixed",
    "逆馬丁（連勝加倉、連虧縮倉）": "Anti-martingale (add on wins, cut on losses)",
    "馬丁（連虧加倉）": "Martingale (add on losses)",
    "加倉倍率": "Add-on multiplier",
    "減倉倍率": "Reduce multiplier",
    "倍率上限": "Max multiplier",
    "倍率下限": "Min multiplier",
    "取樣筆數": "Lookback trades",
    "遠近衰減": "Recency decay",
    "單筆上限": "Max per trade",
    "單筆下限": "Min per trade",
    "啟用波動目標（抗震盪）": "Enable volatility target (anti-whipsaw)",
    "目標年化波動 (%)": "Target annual vol (%)",
    "啟用止損 / 止盈（僅做多引擎支援）": "Enable stop-loss / take-profit (long-only engine)",
    "止損 (%)": "Stop-loss (%)",
    "止盈 (%)": "Take-profit (%)",
    "初始資金 (USDT)": "Initial capital (USDT)",
    "強制刷新數據（清除快取重新下載）": "Force refresh data (clear cache and redownload)",
    "搜尋資產…": "Search asset…",
    "多標的資產選擇": "Multi-asset selection",
    "選擇資產（建議 ≥ 3）": "Select assets (recommend ≥ 3)",
    "多標的權重（對應上面順序；留空＝等權）": "Weights (match order above; blank = equal)",
    "例如 0.5, 0.3, 0.2…": "e.g. 0.5, 0.3, 0.2…",
    "策略程式碼": "Strategy code",
    "策略參數": "Strategy params",
    "策略檔名…": "Filename…",
    "另存檔名": "Save as…",
    "另存": "Save as",
    "載入": "Load",
    "刪除": "Delete",
    "載入既有策略": "Load saved strategy",
    "載入既有策略…": "Load a saved strategy…",
    "選擇策略檔（.py）": "Choose strategy file (.py)",
    "刪除選取的策略檔": "Delete selected strategy file",
    "載入中…": "Loading…",
    "請輸入檔名": "Enter a filename",
    "請先選擇策略檔": "Select a strategy file first",
    "請先在下方選擇要刪除的策略檔": "Select a strategy file below to delete",
    "先寫一個策略，再按執行回測": "Write a strategy, then run the backtest",
    "在左側編輯器寫": "Write in the editor on the left",
    "參數": "Param",
    "最小": "Min",
    "最大": "Max",
    "步長": "Step",
    "最多選 2 個參數（畫熱力圖）": "Up to 2 params (heatmap)",
    "優化指標": "Optimize metric",
    "優化中…": "Optimizing…",
    "完成": "Done",
    "命令面板": "Command palette",
    "命令": "Command",
    "輸入指令…（執行回測 / 切分頁 / 載入策略）": "Type a command… (run / switch tab / load strategy)",
    "沒有符合的指令": "No matching command",
    "檢視": "View",
    "檢視 · 回測結果": "View · Results",
    "檢視 · 使用手冊": "View · Manual",
    "切換 · 單一資產": "Switch · Single asset",
    "切換 · 多籌組合": "Switch · Multi-asset",
    "切換 · 波動目標": "Toggle · Volatility target",
    "切換 · 網格鎖倉": "Toggle · Grid hedge",
    "主題 · 冷灰": "Theme · Slate",
    "主題 · 冷白": "Theme · Light",
    "主題 · 暖紙": "Theme · Paper",
    "切換語言": "Switch language",
    "語言": "Language",
    "台灣": "Taiwan",
    "美國": "United States",
    "台灣（繁體中文）": "Taiwan (Traditional Chinese)",
    "美國（English）": "United States (English)",
    "即將推出": "Coming soon",
    "英文版（USA）即將推出": "English (USA) coming soon",
    "語言：台灣（繁體中文）": "Language: Taiwan (Traditional Chinese)",
    "下載手冊（.md 文字檔）": "Download manual (.md)",
    "手冊尚未載入": "Manual not loaded",
    "已下載手冊": "Manual downloaded",
    "讀取檔案失敗": "Failed to read file",
    "複製程式碼": "Copy code",
    "已複製程式碼": "Code copied",
    "複製失敗（瀏覽器未允許）": "Copy failed (not allowed)",
    "收合／展開左欄": "Collapse / expand left column",
    "跳到主要內容": "Skip to content",
    "先下載，再交給 AI。": "Download it, then hand it to an AI.",
    "你可以把整份手冊下載成 .md 檔，直接貼給 AI，然後向它提出你的需求（例如：撰寫新策略、新增指標、調整回測設定、載入資料），它就能照這份規格幫你實作。建議使用 DeepSeek 的 API，成本較低。": "You can download the whole manual as a .md file, paste it into an AI, and describe what you need (e.g. write a new strategy, add an indicator, adjust backtest settings, load data) — it will implement it to this spec. Using the DeepSeek API is recommended for lower cost.",
    "指標：": "Metric: ",
    "（越大越好）": " (higher is better)",
    "（越小越好）": " (lower is better)",
    "波動目標：倉位 = 基礎倉位 × clip(目標波動 ÷ 平滑後已實現波動, 0.2, 2.0)。高波動自動縮倉、低波動加倉——不砍任何交易，是「倉位公式」不是「濾網」。": "Volatility target: position = base × clip(target vol ÷ smoothed realized vol, 0.2, 2.0). Auto-shrink in high vol, add in low vol — never drops a trade; it's a position formula, not a filter.",
    "可用 pd、np 與多種技術指標（sma、ema、wma、rsi、macd、bollinger、atr、adx、kdj、cci、mfi、obv、vwap…）。用到哪個指標，它的調參欄位會自動出現。df 欄位 open/high/low/close/volume。": "pd/np plus a wide range of technical indicators (sma, ema, wma, rsi, macd, bollinger, atr, adx, kdj, cci, mfi, obv, vwap, …). Params for whichever indicator you use appear automatically. df columns: open/high/low/close/volume.",
    "SMA 週期": "SMA period", "EMA 週期": "EMA period", "WMA 週期": "WMA period", "RMA 週期": "RMA period",
    "DEMA 週期": "DEMA period", "HMA 週期": "HMA period", "標準差 週期": "Stdev period", "Z分數 週期": "Z-score period",
    "RSI 週期": "RSI period", "ROC 週期": "ROC period", "動量 週期": "Momentum period", "TRIX 週期": "TRIX period",
    "MACD 快線週期": "MACD fast period", "MACD 慢線週期": "MACD slow period", "MACD 訊號週期": "MACD signal period",
    "PPO 快線週期": "PPO fast period", "PPO 慢線週期": "PPO slow period", "PPO 訊號週期": "PPO signal period",
    "布林 週期": "Bollinger period", "布林 標準差倍數": "Bollinger std dev mult",
    "ATR 週期": "ATR period", "NATR 週期": "NATR period", "DMI 週期": "DMI period", "ADX 週期": "ADX period",
    "CCI 週期": "CCI period", "MFI 週期": "MFI period", "威廉 週期": "Williams %R period",
    "VWAP 週期": "VWAP period", "VWMA 週期": "VWMA period", "CMF 週期": "CMF period",
    "KDJ 週期": "KDJ period", "KDJ 平滑K": "KDJ smooth K", "KDJ 平滑D": "KDJ smooth D",
    "STOCH 週期": "Stoch period", "STOCH 平滑K": "Stoch smooth K", "STOCH 平滑D": "Stoch smooth D",
    "Aroon 週期": "Aroon period", "Donchian 週期": "Donchian period",
    "AO 快線週期": "AO fast period", "AO 慢線週期": "AO slow period",
    "選擇指標與 1–2 個參數，按「開始優化」。結果會顯示熱力圖與明細表，用來找**穩定的參數區**（而非單一尖峰——尖峰通常是過擬合）。": "Pick a metric and 1–2 params, then click Optimize. You'll get a heatmap and a table to find a **stable parameter region** (not a single spike — spikes are usually overfit).",
    "勾選要掃描的參數（最多 2 個＝畫熱力圖），設定最小 / 最大 / 步長；未勾的用目前「策略參數」的值。組合數上限 400。": "Check the params to scan (up to 2 = heatmap), set min / max / step; unchecked use current values. Max 400 combos.",
    "目前策略沒有可掃描的數值參數（需定義 PARAM_DEFS）。": "This strategy has no numeric params to scan (define PARAM_DEFS).",
    "請至少勾選一個參數": "Select at least one parameter",
    "請至少選擇一種資產": "Select at least one asset",
    "以目前資產 / 週期 / 區間回測": "Backtest with current asset / interval / range",
    "沒有完成的交易": "No completed trades",
    "沒有回傳結果": "No result returned",
    "沒有釘選": "No pins",
    "清除釘選": "Clear pins",
    "已清除釘選": "Pins cleared",
    "釘選目前": "Pin current",
    "先執行回測再釘選": "Run a backtest first",
    "已釘選目前結果": "Current result pinned",
    "上次回測": "Previous run",
    "最新值": "Latest",
    "交易明細": "Trades",
    "交易次數": "Trades",
    "原因": "Reason",
    "方向": "Side",
    "用途": "Role",
    "多": "Long",
    "空": "Short",
    "完整績效指標": "Full metrics",
    "各資產績效": "Per-asset performance",
    "價格與買賣點": "Price & trades",
    "權益曲線": "Equity",
    "滾動指標": "Rolling metrics",
    "成本拖累": "Cost drag",
    "曝險（持倉比例）": "Exposure",
    "毛權益（無成本）": "Gross equity",
    "淨權益": "Net equity",
    "總手續費": "Total fees",
    "成本": "Cost",
    "起點 = 100": "Start = 100",
    "等權買入持有": "Equal-weight buy & hold",
    "買入持有": "Buy & hold",
    "組合權益": "Portfolio",
    "策略權益": "Strategy",
    "直接停損": "Direct stop",
    "回撤": "Drawdown",
    "收盤": "Close",
    "收盤線": "Close line",
    "K線": "Candles",
    "價格": "Price",
    "線性": "Linear",
    "對數": "Log",
    "自動": "Auto",
    "全部": "All",
    "近 1 年": "Last 1y",
    "近 2 年": "Last 2y",
    "近 3 年": "Last 3y",
    "近 5 年": "Last 5y",
    "近 10 年": "Last 10y",
    "自訂": "Custom",
    "總收益": "Total",
    "總收益率": "Total return",
    "年化": "CAGR",
    "年化 (CAGR)": "CAGR",
    "年化波動": "Annual vol",
    "夏普": "Sharpe",
    "夏普比率": "Sharpe",
    "索提諾比率": "Sortino",
    "卡瑪": "Calmar",
    "卡瑪比率": "Calmar",
    "最大回撤": "Max drawdown",
    "勝率": "Win rate",
    "盈虧比": "Profit factor",
    "平均每筆": "Avg trade",
    "平均盈利": "Avg win",
    "平均虧損": "Avg loss",
    "最佳交易": "Best trade",
    "最差交易": "Worst trade",
    "持倉比例": "Exposure",
    "超額報酬": "Excess return",
    "進場時間": "Entry time",
    "進場價": "Entry",
    "出場時間": "Exit time",
    "出場價": "Exit",
    "數量": "Qty",
    "收入": "Proceeds",
    "盈虧": "P&L",
    "收益率": "Return",
    "滾動夏普": "Rolling Sharpe",
    "爆倉次數": "Liquidations",
    "鎖倉次數": "Hedges",
    "解鎖次數": "Unlocks",
    "加單次數": "Add-ons",
    "保證金略過": "Margin skips",
    "網格鎖倉": "Grid hedge",
    "網格開倉": "Grid entries",
    "毛": "Gross",
    "淨": "Net",
    "持倉": "Position",
    "上次": "Prev",
    "引擎 · ": "Engine · ",
    "引擎": "Engine",
    "做多": "Long",
    "做空": "Short",
    "多空": "Long/Short",
    "無法取得設定，請確認後端已啟動": "Failed to load settings; is the backend running?",
    "無法連線後端": "Cannot reach backend",
    "執行失敗": "Run failed",
    "失敗": "Failed",
    "待命": "Idle",
    "待機中": "Idle",
    "回測中…": "Running…",
    "本地 CSV": "Local CSV",
    "本地 CSV（data\\import_csv）": "Local CSV (data\\import_csv)",
    "5 分鐘": "5 min",
    "15 分鐘": "15 min",
    "30 分鐘": "30 min",
    "1 小時": "1 hour",
    "4 小時": "4 hours",
    "6 小時": "6 hours",
    "12 小時": "12 hours",
    "日線": "Daily",
    "週線": "Weekly",
    "比特幣": "Bitcoin",
    "以太幣": "Ethereum",
    "瑞波幣": "XRP",
    "幣安幣": "BNB",
    "狗狗幣": "Dogecoin",
    "艾達幣": "Cardano",
    "比特現金": "Bitcoin Cash",
    "萊特幣": "Litecoin",
    "柴犬幣": "Shiba Inu",
    "波場幣": "TRON",
    "恆星幣": "Stellar",
    "Binance API（線上）": "Binance API (online)",
    "資產": "Asset",
    "找不到資產": "No asset found",
    "模式": "Mode",
    "多空": "Long/Short",
    "槓桿": "Leverage",
    "爆倉：槓桿下權益歸零，回測於該點停止。請降低槓桿或倉位。": "Liquidation: equity hit zero under leverage; the backtest stopped there. Lower leverage or size.",
    "多空（反手）引擎不支援止損/止盈，已忽略這兩個設定。": "The long/short engine does not support SL/TP; both were ignored.",
    "送入「網格鎖倉引擎」（自動加單 / 鎖倉 / 解鎖）": "Send to grid-hedge engine (auto add / hedge / unlock)",
    "已送入網格鎖倉引擎：結果含加單 / 鎖倉 / 解鎖與資金費率。": "Sent to grid-hedge engine: results include add-ons / hedges / unlocks and funding.",
    "未來函數檢查通過：截斷重算與全樣本一致。": "Look-ahead check passed: truncated recompute matches the full sample.",
    "未來函數檢查無法完成（策略無法在截斷資料上重算）。": "Look-ahead check could not complete (strategy can't recompute on truncated data).",
    "Quant-Studio-使用手冊.md": "Quant-Studio-Manual.md"
  };

  const RE = [
    [/^偵測到未來函數（look-ahead），共 (\d+) 處不一致。範例：(.+?)。常見原因：(.+)。$/, (m, n, ex, c) => `Look-ahead detected: ${n} mismatch(es). Example: ${ex}. Common causes: ${c}.`],
    [/^回測 (\d+)\/(\d+)(.*)$/, (m, a, b, rest) => `Backtest ${a}/${b}${rest}`],
    [/^優化 (\d+)\/(\d+)$/, (m, a, b) => `Optimizing ${a}/${b}`],
    [/^完成 · (\d+) 組$/, (m, n) => `Done · ${n} combos`],
    [/^(\d+) 根 · K 線過密，改收盤線$/, (m, n) => `${n} bars · too dense, using close line`],
    [/^(\d+) 根 K 線$/, (m, n) => `${n} bars`],
    [/^視窗 (\d+) 根$/, (m, n) => `Window ${n} bars`],
    [/^(\d+) 幣 · 起點 = 100 可比較$/, (m, n) => `${n} coins · normalized to 100`],
    [/^(\d+) 幣$/, (m, n) => `${n} coins`],
    [/^(\d+) 筆$/, (m, n) => `${n} trades`],
    [/^釘選(\d+) · (.+)$/, (m, n, l) => `Pin${n} · ${l}`],
    [/^載入策略 · (.+)$/, (m, x) => `Load strategy · ${x}`],
    [/^已載入 (.+)$/, (m, x) => `Loaded ${x}`],
    [/^已儲存 (.+)$/, (m, x) => `Saved ${x}`],
    [/^已刪除 (.+)$/, (m, x) => `Deleted ${x}`],
    [/^確定刪除策略檔「(.+)」？.*$/, (m, x) => `Delete strategy file "${x}"? This cannot be undone.`],
    [/^總成本 ≈ (.+)（手續費 ≈ (.+)）$/, (m, a, b) => `Total cost ≈ ${a} (fees ≈ ${b})`],
    [/^權重數量須等於資產數（(\d+)），改用等權$/, (m, n) => `Weights must match assets (${n}); using equal weight`],
    [/^持倉時間 (.+)$/, (m, x) => `Time in market ${x}`],
    [/^；顯示前 (\d+) 名。找「穩定高原」而非單一尖峰。$/, (m, n) => `; showing top ${n}. Look for a stable plateau, not a single spike.`],
    [/^(.+) · (\d+) 幣 · (.+)$/, (m, src, n, iv) => `${src} · ${n} coins · ${iv}`],
    [/^(.+) · (\d+) 根 K 線$/, (m, sym, n) => `${sym} · ${n} bars`]
  ];

  const KEYS = Object.keys(EN).filter((k) => k.length >= 2).sort((a, b) => b.length - a.length);

  let LANG = localStorage.getItem("qs-lang") || "zh-Hant";

  function sub(s) {
    let out = s;
    for (const k of KEYS) if (out.indexOf(k) !== -1) out = out.split(k).join(EN[k]);
    return out;
  }
  function tAny(s) {
    if (LANG !== "en-US" || !s) return s;
    if (EN[s] !== undefined) return EN[s];
    let out = s;
    for (const [re, fn] of RE) { if (re.test(out)) { out = out.replace(re, fn); break; } }
    out = sub(out);
    return out;
  }
  const t = (s) => (LANG === "en-US" ? tAny(s) : s);

  function trStr(s) {
    if (typeof s !== "string" || !s) return s;
    if (EN[s] !== undefined) return EN[s];
    return s.replace(/<extra>([\s\S]*?)<\/extra>/g, (m, inner) => `<extra>${EN[inner] !== undefined ? EN[inner] : sub(inner)}</extra>`);
  }
  function deep(o) {
    if (typeof o === "string") return trStr(o);
    if (Array.isArray(o)) return o.map(deep);
    if (o && typeof o === "object") { const r = {}; for (const k in o) r[k] = deep(o[k]); return r; }
    return o;
  }
  function hookPlotly() {
    if (!window.Plotly || window.Plotly.__i18n) return;
    const np = Plotly.newPlot.bind(Plotly);
    Plotly.newPlot = function (el, data, layout, config) { return np(el, deep(data), deep(layout), config); };
    const rc = Plotly.react && Plotly.react.bind(Plotly);
    if (rc) Plotly.react = function (el, data, layout, config) { return rc(el, deep(data), deep(layout), config); };
    Plotly.__i18n = true;
  }

  const SKIP = ".CodeMirror, #manual, pre, code, script, style, svg, [data-no-i18n]";
  function walk(node) {
    if (node.nodeType === 3) {
      const p = node.parentElement;
      if (!p || p.closest(SKIP)) return;
      if (node.__zh === undefined) node.__zh = node.nodeValue;
      const next = tAny(node.__zh);
      if (node.nodeValue !== next) node.nodeValue = next;
    } else if (node.nodeType === 1) {
      if (node.closest && node.closest(SKIP)) return;
      ["placeholder", "title", "aria-label"].forEach((a) => {
        if (node.hasAttribute(a)) {
          node.__i18n = node.__i18n || {};
          if (node.__i18n[a] === undefined) node.__i18n[a] = node.getAttribute(a);
          const nv = tAny(node.__i18n[a]);
          if (node.getAttribute(a) !== nv) node.setAttribute(a, nv);
        }
      });
      if (node.tagName === "OPTION" || node.tagName === "TEXTAREA") return;
      node.childNodes.forEach(walk);
    }
  }

  let observer = null;
  function startObserver() {
    if (observer) return;
    observer = new MutationObserver((muts) => {
      muts.forEach((m) => {
        if (m.type === "childList") m.addedNodes.forEach((n) => { if (n.nodeType === 1 || n.nodeType === 3) walk(n); });
        else walk(m.target);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title", "aria-label"] });
  }

  function setLang(lang) {
    LANG = lang === "en-US" ? "en-US" : "zh-Hant";
    try { localStorage.setItem("qs-lang", LANG); } catch (e) {}
    document.documentElement.lang = LANG === "en-US" ? "en" : "zh-Hant";
    document.title = LANG === "en-US" ? "Quant Studio · Quant Backtest" : "Quant Studio · 量化回測";
    hookPlotly();
    walk(document.body);
    document.dispatchEvent(new CustomEvent("qs-langchange"));
  }

  window.QS_I18N = { get lang() { return LANG; }, t, tAny, setLang,
    init() { startObserver(); hookPlotly(); document.documentElement.lang = LANG === "en-US" ? "en" : "zh-Hant"; if (LANG === "en-US") { document.title = "Quant Studio · Quant Backtest"; walk(document.body); } } };
})();
