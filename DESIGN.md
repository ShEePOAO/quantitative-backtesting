# DESIGN.md — Quant Studio

Mode: **Operate**（app / 工作台）。設計服務任務，不是表達。

## Direction
「研究帳冊」工作台：淺色紙面、以細線編碼分組、數據用等寬字對齊。刻意跳脫原版深色儀表板，也避開 AI 常見套路（奶油底＋襯線＋陶土色、近黑＋螢光單色、SaaS 圓角卡海、全大寫 eyebrow）。顏色幾乎不用於裝飾，只留給「有意義的數據」（漲/跌/警示）。

方向來源：ui-ux-pro-max `--design-system`（Research Lab palette / Fira）＋ frontend-design（ledger 概念）＋ impeccable operate（單一字族、固定級距、無載入編排動效）。

## Color tokens
預設＝**石墨 × 霧面石英**：冷霧灰紙面 + 石墨近黑墨 + 深钴藍單一強調色；顏色幾乎只留給有意義的數據。以「quieter」原則處理（降飽和、中性色扛主調、冷調灰）。
| token | hex | 用途 |
|---|---|---|
| `--bg` | `#DDE2E5` | app 背景（冷霧灰，頁面帶極淡徑向漸層） |
| `--surface` | `#E6EAEC` | 主體面（霧面石英，降亮降反差） |
| `--surface-2` | `#D8DEE1` | 第二中性層（側欄/表頭） |
| `--field` | `#EDF1F2` | 輸入欄/編輯器欄位底（帶 inset 陰影） |
| `--ink` | `#14171A` | 主文字（石墨近黑） |
| `--ink-2` | `#454C53` | 次文字 |
| `--ink-3` | `#575F66` | 說明/placeholder（≥4.5:1） |
| `--line` | `#CBD2D6` | hairline |
| `--line-strong` | `#B0B8BE` | 強調分隔 |
| `--accent` | `#2C4796` | 唯一互動色（深钴藍）：主要動作、選取、focus；主按鈕用同系漸層 |
| `--up` | `#1E7A5E` | 正報酬（文字） |
| `--down` | `#C0392B` | 負報酬（文字） |
| `--warn` | `#A15C00` | 警示 |
| `--chart-bh` | `#868E95` | 買入持有（虛線，需清楚可見） |
| chart up / down | `#2C9E7E` / `#D9574C` | K 線 / 權益 |

**深度與光影（質感來源）**：頁面用極淡徑向漸層撐出背景深度；面板以 `--shadow-sm/--shadow-md`（帶偏移的柔陰影）分層，不用「卡片海」；輸入框 inset 內陰影；主按鈕同系漸層＋頂部高光。深度一律用帶偏移的柔陰影（非彩色光暈、非硬陰影）。

**主題機制**：色票全為 CSS 變數；`<html data-theme>` 可切換 `warm`（暖灰）、`slate`（冷灰）、`paper`（冷白），預設（無屬性）＝奶油暖紙；圖表顏色於 render 時讀取變數，故主題一致套用。可用 `?theme=warm|slate|paper` 預覽。

規則：accent 只用於主要動作 / 目前選取 / 狀態；色彩不得單獨承載意義（漲跌同時附正負號或文字）。買入持有線以「暖灰實色虛線、寬 1.8」呈現，確保對比足夠而非裝飾。

> 註：impeccable 偵測器對「暖色頁面底」會提示 cream/beige 套路；此處為使用者逐版比較後**明確選定**的方向，依 skill 規則（使用者明示優先）保留，非預設反射。

## Type
- UI/標題/內文：**IBM Plex Sans**（IBM 為資料/技術介面設計，專業且不流於 Inter 的泛用）。
- 程式碼與所有數值（metrics、表格、報價、時間）：**Fira Code**，`font-variant-numeric: tabular-nums`。
- CJK 後備：Noto Sans TC → system。
- 固定 rem 級距（非 fluid）：12 / 13 / 14 / 16 / 20 / 26 / 32。對話線長 65–75ch；表格可更密。
- 不用全大寫標籤；標籤句首大寫即可。不用 display font 於 UI 標籤。

## Charts
- 只留水平格線（去除垂直格線）、軸線極淡；y 軸千分位（`,.0f`）。
- 權益曲線線尾加**最新值**圓點＋標籤；買入持有為較細虛線，策略為較粗實線。
- 統一 hover（x unified）；>500 根 K 線自動改收盤線。

## Icons
一致的細線 SVG 圖示（stroke 1.5–1.6、currentColor），用於區塊標題；不用 emoji、不混用圖示庫。

## Layout
左「策略台」（程式編輯器＋參數＋回測設定，sticky、可捲）｜右「讀數區」（績效 → 權益 → 回撤 → 價格/買賣點 → 交易明細）。行動版斷點（1024 / 768）折疊為單欄。以 hairline 與留白編碼分組，不用卡片陰影、不用圓角卡海。

## Components / states
所有互動元件具備 default / hover / focus-visible / active / disabled / loading / error。載入用骨架（skeleton）非置中 spinner。空狀態引導操作。原生 scrollbar 僅做低調主題化。

### 參數區：Inspector + 調音台
- 每個參數是一**列**：label 在左（灰）、控制項在右；數值等寬、右對齊。
- 有界數值附**單位 chip**（USDT / × / %）與**同步滑桿**（cobalt 滑塊），像調音台；滑桿為 `aria-hidden` 裝飾，數值框才是唯一可存取/存取的控件。
- 無界欄位（初始資金）只給單位 chip；策略參數（PARAM_DEFS）動態生成時同樣套用滑桿。

## Motion
150–250ms；只表達狀態（回測完成後結果區的一次淡入、執行中 disabled＋骨架）。**（使用者要求）所有動畫一律播放：不使用 `prefers-reduced-motion` 停用動畫**，新舊動畫皆不受系統設定影響。

## Animation / interaction layer
- **masthead**：一層極淡的淺色 mesh `gradient` 微光（GalaxyJS，低干擾）。
- **載入**：骨架佔位（skeleton）＋ masthead 底部確定式進度條；不播角色動畫。
- **互動升級**：刪除策略 `Galaxy.confirm`；讀數格與表格列 hover。
- 未使用 GalaxyJS 的 `gx-*` UI 元件。
- （已移除：載入爬蟲 spider 動畫。）

## Interaction & feedback（無框架）
以「動效表達狀態、非裝飾」為原則：
- **執行回饋**：`/api/run` 以 NDJSON 串流回報進度事件；多幣時 masthead 底部顯示**確定式進度條**與「回測 i/n · 資產」。
- **數字進場**：metrics 讀數以 450ms count-up 進場（tabular-nums、尊重 reduced-motion）。
- **圖表進場**：權益/回撤/價格圖以 clip-path wipe 一次畫入。
- **微互動**：分頁底線滑動指示器、可折疊區塊內容淡入、複製程式碼回饋、`Cmd/Ctrl+Enter` 執行、指標 label tooltip（hover/focus）。
- **品牌**：標題列小圖示載入時自我描繪一次。
- 全部於 `prefers-reduced-motion` 下退化為靜止。

## Interactive controls
- **參數**：拖曳數值 scrub（按住左右拖）＋對應滑桿＋單位 chip；數值框為唯一可存取控件。
- **開關**：toggle 樣式取代原生 checkbox（啟用波動目標/止損止盈/網格鎖倉/強制刷新）。
- **資產**：可搜尋 combobox（輸入即篩選，↑↓/⏎）。
- **日期**：雙把手範圍滑桿（拖曳即切「自訂」）。
- **圖表**：權益圖 線性 / 對數座標切換；價格圖 自動 / K線 / 收盤線；滾輪縮放。
- **對比**：幽靈曲線（上次回測）＋「釘選目前」可疊多條結果曲線比較（`釘選1 · BTC` …），可「清除釘選」。
- **版面**：左欄可拖曳調寬（雙擊回復預設）、拖曳軸按鈕收合為專注模式（結果全寬）；寬度與收合狀態記憶於 localStorage。
- **命令面板**：`Cmd/Ctrl+K`（執行、切分頁、切模式、載入策略、切主題）。

## Refuse (from craft-floor)
無 eyebrow、無漸層文字、無裝飾玻璃模糊、無彩色 border-left、無硬陰影、無 emoji 當 icon（用行內 SVG）、數字不用裝飾性 mono。
