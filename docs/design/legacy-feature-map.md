# 旧项目功能映射

## 目标

新项目继续使用同一套公开代码 + 本地私有数据的边界。旧 Streamlit 项目作为功能参考和私有数据来源；真实账户、交易记录、AI 历史和 AI Provider 配置只导入新项目的 `storage/local/app.db`，不写入公开模板或文档。

## 功能映射

| 旧项目功能 | 新项目模块 | 当前状态 | 后续实现重点 |
| --- | --- | --- | --- |
| Dashboard 总览：账户、持仓、市值、成本收益、行情状态 | 总览 | 已接 FastAPI 本地状态；标的状态表展示现价、持仓、成本/市值、盈亏、仓位、MA、RSI、回撤和今日信号，价格/市值优先使用真实报价，样例行情不参与市值和信号展示 | 补风险事件、信号历史 |
| K 线走势：1日、五日、日K、周K、月K | K线工作台 | 已有第一版；1日/五日为蜡烛图，区间统计和数据状态在图表下方；日内横轴按交易所本地时间展示；图表读数条展示 OHLC、成交量和 MA20/60/120/200；日 K/非日内图展示买卖交易标记 | 增加交易标记筛选、图上事件标记 |
| Settings：总资产、股票池、持仓目标、止盈止损、AI URL/模型/密钥 | 数据管理 | 已接 SQLite 状态，密钥只显示掩码；总资产、股票池、持仓目标和 AI Provider 统一放在数据管理页；支持 AI `/models` 连接测试 | 增加字段级错误提示、批量编辑 |
| 交易记录：金额 + 单支成本反算碎股，重算持仓成本 | 数据管理 | 已接 SQLite 状态并导入旧流水，支持新增、编辑、删除；支持 CSV/TSV 交易流水解析预览和导入；旧 Settings 的交易流水拆到数据管理页 | XLSX 前端解析、撤销/恢复 |
| Signal 加减仓：趋势、回撤、RSI、仓位缺口、现金、止盈止损 | 策略研究 | 已迁移旧 `signal_engine` | 增加交易标记、信号历史和手动确认流程 |
| 策略档案：保守、平衡、进取、自定义，ETF/核心/卫星分层 | 策略研究 | 已接后端参数，支持基础参数和分层加减仓参数编辑；旧 Settings 的加减仓策略设置拆到策略研究页 | 增加参数校验、复制档案、回测保存到档案 |
| 策略研究回测：买入持有、定投、MA 风控、回调加仓 | 策略研究 | 已迁移旧 `backtest_engine` 摘要、旧版函数表、资金曲线和单策略交易记录 | 增加参数对比、回测保存 |
| AI 综合建议：账户、持仓、交易、行情、信号、新闻上下文 | AI建议 | 已导入旧 AI 日历，页面只保留每日 OpenAI-compatible 生成和今日追问；外部生成上下文包含账户、持仓、交易流水、MA/RSI/回撤信号、日内走势摘要和最近新闻标题；生成/追问失败可重试上次动作 | 增加对话摘要压缩 |
| 行情缓存：交易时段短缓存，非交易时段会话缓存 | FastAPI 行情模块 | 报价已支持 yfinance 优先、Nasdaq 延迟报价兜底、sample 最后兜底；K 线历史在 yfinance 不可用时返回 sample 并标明 source | 增加源状态、stale fallback、手动刷新语义 |
| 公私数据分离：模板公开、本地数据私有 | storage + scripts | 已有 | 扩展 public safety 扫描和首次启动导入模板 |

## 数据口径

- 现金口径沿用旧项目：`现金 = 总资产 - 持仓成本`。
- 持仓成本由交易流水重算，卖出时按当时平均成本减少成本值。
- 市值和浮动盈亏只用于风险/收益展示，不反推可用现金。
- 交易流水字段保持兼容：`date`、`ticker`、`action`、`shares`、`unit_price`、`amount`、`note`。
- 目标仓位、止盈线、止损线使用 0 到 1 的比例，界面以百分比编辑。
- 前端状态优先从 `GET /api/trading-state` 读取，保存到 `PUT /api/trading-state`；API 不可用时保留 localStorage 兜底。
- 股票池来自本地交易状态，`/api/watchlist`、`/api/quotes`、`/api/signals` 和 `/api/backtests` 都围绕同一份本地状态工作。
- 旧项目私有导入命令：`python3 scripts/import_legacy_private_data.py`。
- 当前已导入旧项目本地状态：股票池 `VOO, QQQM, NVDA, NOK, MSFT, MRVL`，交易流水 24 条，AI 日历 13 条。该数据在 `storage/local/app.db`，被 `.gitignore` 排除。
- AI 设置保存在 `ai_settings_v1`，公开 API 只返回 URL、模型、`hasApiKey` 和掩码。

## 旧 Settings 拆分原则

旧 Streamlit 项目把账户、股票池、持仓目标、交易流水、AI Provider 和策略档案集中在 Settings。新项目为了后续维护拆成三个入口：

- `数据管理`：总资产、股票池、持仓目标、止盈止损、AI URL/模型/密钥、AI 连接测试、交易流水和 CSV/TSV 本地导入。
- `设置`：安全边界说明。
- `策略研究`：保守/平衡/进取/自定义档案，基础信号参数，ETF/核心/卫星分层加减仓参数，后端信号和回测研究。

这三个入口仍然写入同一份 `storage/local/app.db`，公共模板和私有运行数据继续分离。

## Review 拆分

- `apps/web/src/features/platform/trading-data.ts`：交易流水、持仓成本、校验口径。
- `apps/web/src/features/platform/views/dashboard-view.tsx`：账户总览和标的状态表。
- `apps/web/src/features/platform/views/data-management-view.tsx`：总资产、股票池、持仓目标、交易流水录入/编辑/删除、AI Provider 设置与账户口径。
- `apps/web/src/features/platform/views/settings-view.tsx`：公开/私有数据边界。
- `apps/web/src/features/platform/views/strategy-view.tsx`：策略档案参数、ETF/核心/卫星分层编辑、后端信号台和回测摘要。
- `apps/web/src/features/platform/views/ai-advice-view.tsx`：AI 日历、旧建议记录、每日外部生成和今日追问。
- `apps/api/app/modules/trading_data.py`：本地状态、派生持仓、账户摘要、校验。
- `apps/api/app/modules/ai_advice.py`：AI 日历记录、每日外部生成和追问。
- `apps/api/app/modules/ai_settings.py`：AI Provider 设置和密钥掩码。
- `apps/api/app/modules/signal_engine.py`：旧项目信号规则迁移。
- `apps/api/app/modules/backtest_engine.py`：旧项目回测规则迁移。
- `apps/api/app/modules/market.py`：行情源、样例 K 线、交易日时间轴。
