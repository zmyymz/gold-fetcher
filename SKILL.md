---
name: gold_fetcher
description: 从 Yahoo Finance 获取黄金(XAUUSD) RSI 技术指标及 VIX 恐慌指数数据，用于辅助贵金属投资决策。提供超买/超卖信号、市场情绪判断等技术分析参考，无需 API Key。
---

# 黄金市场技术指标 Skill (gold_fetcher)

从 Yahoo Finance 公开接口获取 **XAUUSD 黄金 RSI 指标** 和 **VIX 恐慌指数** 数据，输出 JSON 格式，无需 API Key。

## 包含工具

| 脚本 | 功能 | 数据源 |
|------|------|--------|
| `fetch_gold_rsi.py` | 获取黄金 RSI(相对强弱指数) | Yahoo Finance GC=F |
| `fetch_vix.py` | 获取 VIX 恐慌指数 | Yahoo Finance ^VIX |

## 适用场景

当用户询问以下内容时使用本 Skill：
- **黄金 RSI 指标**：黄金是否超买/超卖、RSI 当前值、技术面分析
- **VIX 恐慌指数**：市场情绪如何、恐慌程度、波动率水平
- **黄金投资参考**：结合 RSI + VIX 判断黄金买卖时机

## 使用方式

### 1. 获取黄金 RSI 数据

```bash
python fetch_gold_rsi.py
```

**带参数调用（key=value 格式，推荐）：**

```bash
python fetch_gold_rsi.py period=1y interval=1wk rsi_period=14 limit=52
```

**带参数调用（JSON 格式）：**

```bash
python fetch_gold_rsi.py "{\"period\": \"1y\", \"interval\": \"1wk\", \"limit\": 52}"
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | string | `3mo` | 历史数据跨度：`1mo`/`3mo`/`6mo`/`1y`/`2y` |
| `interval` | string | `1d` | K线粒度：`1d`(日线)/`1wk`(周线)/`1h`(小时线)/`15m`(15分钟线) |
| `rsi_period` | int | `14` | RSI 计算周期 |
| `limit` | int | `30` | 返回最新 N 条数据 |

**RSI 信号解读：**

| RSI 范围 | 信号 | 含义 |
|----------|------|------|
| > 70 | `overbought` | 超买区间，可能面临回调压力 |
| 30~70 | `neutral` | 中性区间，无明显信号 |
| < 30 | `oversold` | 超卖区间，可能存在反弹机会 |

### 2. 获取 VIX 恐慌指数

```bash
python fetch_vix.py
```

**带参数调用：**

```bash
python fetch_vix.py period=6mo interval=1d limit=50
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | string | `3mo` | 历史数据跨度：`1mo`/`3mo`/`6mo`/`1y`/`2y`/`5y` |
| `interval` | string | `1d` | K线粒度：`1d`(日线)/`1wk`(周线)/`1mo`(月线)/`1h`(小时线) |
| `limit` | int | `30` | 返回最新 N 条数据 |

**VIX 市场情绪解读：**

| VIX 范围 | 情绪标签 | 含义 |
|----------|----------|------|
| < 10 | `extreme_calm` | 极度平静，市场自满 |
| 10~15 | `calm` | 平静 |
| 15~20 | `normal` | 正常波动，健康区间 |
| 20~30 | `uncertainty` | 不确定性，波动加剧 |
| 30~40 | `fear` | 恐慌，波动性高 |
| > 40 | `extreme_fear` | 极度恐慌，历史极端水平 |

## 返回结构

### RSI 返回示例（关键字段）

```json
{
  "success": true,
  "symbol": "XAUUSD (GC=F)",
  "interval": "1d",
  "rsi_period": 14,
  "latest_rsi": 55.32,
  "latest_signal": "neutral",
  "latest_close": 2650.80,
  "latest_datetime": "2025-01-10 00:00 UTC",
  "signal_description": "RSI 在 30~70，处于中性区间，暂无明显超买或超卖信号",
  "data": [...],
  "total": 30,
  "fetched_at": "2025-01-10 12:00 UTC"
}
```

### VIX 返回示例（关键字段）

```json
{
  "success": true,
  "symbol": "VIX (^VIX) - CBOE Volatility Index",
  "interval": "1d",
  "latest_vix": 18.25,
  "latest_sentiment": "normal",
  "latest_sentiment_cn": "正常波动",
  "latest_datetime": "2025-01-10 00:00 UTC",
  "period_high": 28.50,
  "period_low": 12.30,
  "period_avg": 16.82,
  "data": [...],
  "total": 30,
  "fetched_at": "2025-01-10 12:00 UTC"
}
```

## 注意事项

- **无需 API Key**：使用 Yahoo Finance 公开接口，无需注册或配置密钥
- **网络要求**：需要能访问 `query1.finance.yahoo.com`（可能需要代理）
- **小时/分钟线限制**：`1h` 仅支持近期数据，`15m` 仅支持近 7 天
- **数据延迟**：Yahoo Finance 数据通常有 15~20 分钟延迟
- **PowerShell 兼容**：支持 key=value 格式传参，避免 PowerShell JSON 引号转义问题

## 异常处理

- 如果返回 `"success": false`，检查 `error` 字段获取错误原因
- 常见错误：网络不通、数据不足（历史数据太短无法计算 RSI）
- 请求超时默认 15 秒，确保网络连接正常
