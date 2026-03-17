#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch XAUUSD Gold RSI (Relative Strength Index) Data
获取 XAUUSD 黄金的 RSI 技术指标数据

功能特性:
- 从 Yahoo Finance 获取黄金(XAUUSD)历史价格数据
- 计算 RSI 指标（支持自定义周期，默认14）
- 支持多个时间粒度（1d/1h/1wk 等）
- 返回最新 RSI 值及历史序列
- 附带超买/超卖信号判断

RSI 信号说明:
- RSI > 70: 超买区间，可能面临回调压力
- RSI < 30: 超卖区间，可能存在反弹机会
- RSI 在 30~70: 中性区间

输出格式: JSON
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class RSIDataPoint:
    """RSI 数据点"""
    datetime: str
    close: float
    rsi: Optional[float]
    signal: str  # "overbought" / "oversold" / "neutral" / "N/A"


class GoldRSIFetcher:
    """
    XAUUSD 黄金 RSI 指标获取器

    通过 Yahoo Finance 公开接口获取黄金价格历史数据，
    并在本地计算 RSI 技术指标，无需 API Key。
    """

    SYMBOL = "GC=F"  # Yahoo Finance 黄金期货代码（等同 XAUUSD 走势）

    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    def fetch(
        self,
        period: str = "3mo",
        interval: str = "1d",
        rsi_period: int = 14,
        limit: int = 30,
    ) -> Dict:
        """
        获取 XAUUSD 黄金 RSI 数据

        Args:
            period: 历史数据时间跨度
                - "1mo": 最近1个月
                - "3mo": 最近3个月（默认）
                - "6mo": 最近6个月
                - "1y":  最近1年
                - "2y":  最近2年
            interval: K线时间粒度
                - "1d":  日线（默认）
                - "1wk": 周线
                - "1h":  小时线（仅支持近期数据）
                - "15m": 15分钟线（仅支持近7天）
            rsi_period: RSI 计算周期，默认14
            limit: 返回数据条数（最新的 N 条），默认30

        Returns:
            包含 RSI 数据的字典:
            - symbol: 交易品种
            - interval: K线粒度
            - rsi_period: RSI 周期
            - latest_rsi: 最新RSI值
            - latest_signal: 最新信号（overbought/oversold/neutral）
            - latest_close: 最新收盘价（美元）
            - data: RSI历史数据列表
            - fetched_at: 获取时间
        """
        # 拉取价格数据
        closes, timestamps = self._fetch_price_data(period, interval)

        if len(closes) < rsi_period + 1:
            return {
                "success": False,
                "error": f"数据不足，需要至少 {rsi_period + 1} 个数据点，当前仅有 {len(closes)} 个",
                "symbol": "XAUUSD",
            }

        # 计算 RSI 序列
        rsi_values = self._calc_rsi(closes, rsi_period)

        # 构造数据点列表
        data_points: List[RSIDataPoint] = []
        for i, (ts, close) in enumerate(zip(timestamps, closes)):
            rsi_val = rsi_values[i]
            if rsi_val is None:
                signal = "N/A"
            elif rsi_val >= 70:
                signal = "overbought"
            elif rsi_val <= 30:
                signal = "oversold"
            else:
                signal = "neutral"

            dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            data_points.append(
                RSIDataPoint(
                    datetime=dt_str,
                    close=round(close, 2),
                    rsi=round(rsi_val, 2) if rsi_val is not None else None,
                    signal=signal,
                )
            )

        # 只取最新 limit 条
        data_points = data_points[-limit:]

        latest = data_points[-1]

        return {
            "success": True,
            "symbol": "XAUUSD (GC=F)",
            "interval": interval,
            "rsi_period": rsi_period,
            "latest_rsi": latest.rsi,
            "latest_signal": latest.signal,
            "latest_close": latest.close,
            "latest_datetime": latest.datetime,
            "signal_description": self._signal_desc(latest.signal),
            "data": [asdict(dp) for dp in data_points],
            "total": len(data_points),
            "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }

    def _fetch_price_data(self, period: str, interval: str):
        """从 Yahoo Finance 获取历史收盘价及时间戳"""
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(self.SYMBOL)}"
            f"?range={period}&interval={interval}&includePrePost=false"
        )

        req = urllib.request.Request(url, headers=self.headers)

        with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        result = raw.get("chart", {}).get("result", [])
        if not result:
            error_msg = raw.get("chart", {}).get("error", {})
            raise ValueError(f"Yahoo Finance 返回无数据: {error_msg}")

        chart = result[0]
        timestamps = chart.get("timestamp", [])
        closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])

        # 过滤掉 None 值（停牌等）
        pairs = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
        if not pairs:
            raise ValueError("收盘价数据为空")

        timestamps_clean, closes_clean = zip(*pairs)
        return list(closes_clean), list(timestamps_clean)

    def _calc_rsi(self, closes: List[float], period: int) -> List[Optional[float]]:
        """
        使用 Wilder 平滑法计算 RSI

        前 period 个数据点返回 None（数据不足），
        之后使用 Wilder 平均增益/平均损失计算 RSI。
        """
        n = len(closes)
        rsi_list: List[Optional[float]] = [None] * n

        if n <= period:
            return rsi_list

        # 计算每日涨跌
        deltas = [closes[i] - closes[i - 1] for i in range(1, n)]

        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        # 初始平均增益/损失（简单平均，作为种子值）
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # 第一个 RSI 值对应 closes[period]
        def _rsi_from_avg(avg_g, avg_l):
            if avg_l == 0:
                return 100.0
            rs = avg_g / avg_l
            return 100.0 - (100.0 / (1.0 + rs))

        rsi_list[period] = _rsi_from_avg(avg_gain, avg_loss)

        # Wilder 平滑递推
        # 正确顺序：先用当前 avg 计算 RSI，再用当前 delta 更新 avg 供下一步使用
        # gains[i] 表示 closes[i+1] - closes[i] 的涨幅，对应下一根K线的输入
        for i in range(period, n - 1):
            # 用当前K线收盘价对应的涨跌更新 avg（closes[i+1] - closes[i]）
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rsi_list[i + 1] = _rsi_from_avg(avg_gain, avg_loss)

        return rsi_list

    @staticmethod
    def _signal_desc(signal: str) -> str:
        desc_map = {
            "overbought": "RSI > 70，处于超买区间，黄金可能面临短期回调压力",
            "oversold": "RSI < 30，处于超卖区间，黄金可能存在技术性反弹机会",
            "neutral": "RSI 在 30~70，处于中性区间，暂无明显超买或超卖信号",
            "N/A": "数据不足，无法计算 RSI 信号",
        }
        return desc_map.get(signal, "")


def main():
    """
    命令行入口

    从命令行接收 JSON 格式参数，获取 XAUUSD 黄金 RSI 数据

    参数格式:
        {
            "period":     "3mo",   # 历史数据跨度 (1mo/3mo/6mo/1y/2y)
            "interval":   "1d",    # K线粒度 (1d/1wk/1h/15m)
            "rsi_period": 14,      # RSI 周期，默认14
            "limit":      30       # 返回最新 N 条数据，默认30
        }

    使用示例:
        # 获取日线 RSI(14)，最近3个月，返回30条
        python fetch_gold_rsi.py

        # 获取周线 RSI(14)，最近1年，返回52条
        python fetch_gold_rsi.py '{"period": "1y", "interval": "1wk", "limit": 52}'

        # 获取小时线 RSI(9)，最近1个月，返回50条
        python fetch_gold_rsi.py '{"period": "1mo", "interval": "1h", "rsi_period": 9, "limit": 50}'
    """
    period = "3mo"
    interval = "1d"
    rsi_period = 14
    limit = 30

    params = _parse_args()
    if params:
        period = params.get("period", period)
        interval = params.get("interval", interval)
        try:
            rsi_period = int(params.get("rsi_period", rsi_period))
            limit = int(params.get("limit", limit))
        except (ValueError, TypeError) as e:
            print(f"警告: 参数类型转换失败 ({e})，使用默认数值参数", file=sys.stderr)

    fetcher = GoldRSIFetcher()
    try:
        result = fetcher.fetch(period=period, interval=interval, rsi_period=rsi_period, limit=limit)
    except Exception as e:
        result = {"success": False, "error": str(e), "symbol": "XAUUSD"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── PowerShell 兼容：支持多个 sys.argv 片段拼接（单引号传参会被 shell 拆分）
def _merge_argv() -> None:
    """将 sys.argv[1:] 合并成一个字符串，解决 PowerShell 拆分 JSON 参数的问题。"""
    if len(sys.argv) > 2:
        merged = " ".join(sys.argv[1:])
        sys.argv[1:] = [merged]


def _parse_args() -> dict:
    """
    解析命令行参数，支持两种格式：
    1. JSON 字符串: python fetch_gold_rsi.py '{"period": "1y"}'
    2. key=value 参数: python fetch_gold_rsi.py period=1y interval=1wk limit=5
    """
    if len(sys.argv) < 2:
        return {}

    raw = " ".join(sys.argv[1:])

    # 尝试解析为 JSON
    for candidate in [raw, sys.argv[1]]:
        stripped = candidate.strip().strip("'\"")
        try:
            result = json.loads(stripped)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 回退到 key=value 格式
    params = {}
    for token in sys.argv[1:]:
        if "=" in token:
            k, v = token.split("=", 1)
            params[k.strip()] = v.strip()
    return params


if __name__ == "__main__":
    main()
