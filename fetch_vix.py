#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch VIX Index Data from Yahoo Finance
从 Yahoo Finance 获取 VIX 恐慌指数数据

功能特性:
- 获取 VIX（CBOE Volatility Index）历史数据
- 支持多个时间粒度（1d/1wk/1mo 等）
- 附带市场情绪信号判断
- 返回最新值及历史序列

VIX 市场情绪说明:
- VIX < 15:  市场极度平静，投资者自满情绪较高
- VIX 15~20: 市场正常波动区间
- VIX 20~30: 市场出现不确定性，波动加剧
- VIX 30~40: 市场恐慌，波动性较高
- VIX > 40:  市场极度恐慌（历史上仅少数极端事件）

输出格式: JSON
"""

import json
import urllib.request
import urllib.parse
import ssl
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class VIXDataPoint:
    """VIX 数据点"""
    datetime: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: float
    sentiment: str   # "extreme_fear" / "fear" / "uncertainty" / "normal" / "calm" / "extreme_calm"
    sentiment_cn: str


class VIXFetcher:
    """
    VIX 恐慌指数获取器

    通过 Yahoo Finance 公开接口获取 CBOE VIX 指数历史数据，无需 API Key。
    VIX 代码为 ^VIX。
    """

    SYMBOL = "^VIX"

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
        limit: int = 30,
    ) -> Dict:
        """
        获取 VIX 恐慌指数数据

        Args:
            period: 历史数据时间跨度
                - "1mo": 最近1个月
                - "3mo": 最近3个月（默认）
                - "6mo": 最近6个月
                - "1y":  最近1年
                - "2y":  最近2年
                - "5y":  最近5年
            interval: K线时间粒度
                - "1d":  日线（默认）
                - "1wk": 周线
                - "1mo": 月线
                - "1h":  小时线（仅支持近期数据）
            limit: 返回数据条数（最新的 N 条），默认30

        Returns:
            包含 VIX 数据的字典:
            - symbol: 指数名称
            - interval: K线粒度
            - latest_vix: 最新VIX值
            - latest_sentiment: 最新市场情绪（英文）
            - latest_sentiment_cn: 最新市场情绪（中文）
            - latest_datetime: 最新数据时间
            - period_high: 时间段内最高值
            - period_low: 时间段内最低值
            - period_avg: 时间段内平均值
            - data: VIX历史数据列表
            - fetched_at: 获取时间
        """
        raw_data = self._fetch_raw(period, interval)

        timestamps = raw_data["timestamps"]
        opens      = raw_data["opens"]
        highs      = raw_data["highs"]
        lows       = raw_data["lows"]
        closes     = raw_data["closes"]

        if not closes:
            return {
                "success": False,
                "error": "获取到的 VIX 数据为空",
                "symbol": "VIX",
            }

        data_points: List[VIXDataPoint] = []
        for ts, o, h, l, c in zip(timestamps, opens, highs, lows, closes):
            sentiment, sentiment_cn = self._get_sentiment(c)
            dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            data_points.append(VIXDataPoint(
                datetime=dt_str,
                open=round(o, 2) if o is not None else None,
                high=round(h, 2) if h is not None else None,
                low=round(l, 2) if l is not None else None,
                close=round(c, 2),
                sentiment=sentiment,
                sentiment_cn=sentiment_cn,
            ))

        # 只取最新 limit 条
        data_points = data_points[-limit:]

        closes_all = [dp.close for dp in data_points]
        latest = data_points[-1]

        return {
            "success": True,
            "symbol": "VIX (^VIX) - CBOE Volatility Index",
            "interval": interval,
            "latest_vix": latest.close,
            "latest_sentiment": latest.sentiment,
            "latest_sentiment_cn": latest.sentiment_cn,
            "latest_datetime": latest.datetime,
            "period_high": max(closes_all),
            "period_low": min(closes_all),
            "period_avg": round(sum(closes_all) / len(closes_all), 2),
            "sentiment_guide": {
                "< 15":  "极度平静 - 市场自满，潜在风险被低估",
                "15~20": "正常波动 - 市场处于健康区间",
                "20~30": "不确定性 - 市场波动加剧，需关注风险",
                "30~40": "恐慌 - 市场情绪较差，波动性高",
                "> 40":  "极度恐慌 - 历史极端水平，市场剧烈动荡",
            },
            "data": [asdict(dp) for dp in data_points],
            "total": len(data_points),
            "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }

    def _fetch_raw(self, period: str, interval: str) -> Dict:
        """从 Yahoo Finance 获取原始 OHLC 数据"""
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
        timestamps_raw = chart.get("timestamp", [])
        quote = chart.get("indicators", {}).get("quote", [{}])[0]

        opens_raw  = quote.get("open", [])
        highs_raw  = quote.get("high", [])
        lows_raw   = quote.get("low", [])
        closes_raw = quote.get("close", [])

        # 过滤 close 为 None 的条目，并按日期去重（保留最新一条，处理盘中重复数据）
        seen_dates = {}
        for ts, o, h, l, c in zip(timestamps_raw, opens_raw, highs_raw, lows_raw, closes_raw):
            if c is None:
                continue
            # 以日期（UTC）为 key，后出现的覆盖前面的（保留最新盘中数据）
            date_key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            seen_dates[date_key] = (ts, o, h, l, c)

        filtered = list(seen_dates.values())
        if not filtered:
            raise ValueError("VIX 收盘价数据为空")

        ts_list, o_list, h_list, l_list, c_list = zip(*filtered)
        return {
            "timestamps": list(ts_list),
            "opens":      list(o_list),
            "highs":      list(h_list),
            "lows":       list(l_list),
            "closes":     list(c_list),
        }

    @staticmethod
    def _get_sentiment(vix: float):
        """根据 VIX 值返回市场情绪标签"""
        if vix >= 40:
            return "extreme_fear", "极度恐慌"
        elif vix >= 30:
            return "fear", "恐慌"
        elif vix >= 20:
            return "uncertainty", "不确定性"
        elif vix >= 15:
            return "normal", "正常波动"
        elif vix >= 10:
            return "calm", "平静"
        else:
            return "extreme_calm", "极度平静"


def _parse_args() -> dict:
    """
    解析命令行参数，支持两种格式：
    1. JSON 字符串: python fetch_vix.py '{"period": "1y"}'
    2. key=value 参数: python fetch_vix.py period=1y interval=1wk limit=50
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


def main():
    """
    命令行入口

    从命令行接收参数，获取 VIX 恐慌指数数据

    参数格式 (key=value 或 JSON):
        period    历史数据跨度 (1mo/3mo/6mo/1y/2y/5y)，默认 3mo
        interval  K线粒度 (1d/1wk/1mo/1h)，默认 1d
        limit     返回最新 N 条数据，默认 30

    使用示例:
        # 获取日线 VIX，最近3个月（默认）
        python fetch_vix.py

        # 获取周线 VIX，最近1年，返回52条
        python fetch_vix.py period=1y interval=1wk limit=52

        # 获取日线 VIX，最近6个月，返回10条
        python fetch_vix.py period=6mo limit=10
    """
    period   = "3mo"
    interval = "1d"
    limit    = 30

    params = _parse_args()
    if params:
        period   = params.get("period", period)
        interval = params.get("interval", interval)
        try:
            limit = int(params.get("limit", limit))
        except (ValueError, TypeError) as e:
            print(f"警告: 参数类型转换失败 ({e})，使用默认数值参数", file=sys.stderr)

    fetcher = VIXFetcher()
    try:
        result = fetcher.fetch(period=period, interval=interval, limit=limit)
    except Exception as e:
        result = {"success": False, "error": str(e), "symbol": "VIX"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
