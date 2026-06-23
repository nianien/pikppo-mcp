from datetime import datetime, timedelta, timezone

import httpx

from app.models.stock import (
    Announcement,
    DividendRecord,
    FinancialIndicator,
    KlinePoint,
    StockAnnouncements,
    StockDividends,
    StockFundamentals,
    StockHistory,
    StockQuote,
)

# 东方财富：免费、无需 key，一套 secid={market}.{code} 统一覆盖 A股/港股/美股
_SUGGEST = "https://searchapi.eastmoney.com/api/suggest/get"  # 代码/名称/美股 ticker → secid
_QUOTE = "https://push2.eastmoney.com/api/qt/stock/get"  # 实时快照
_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"  # 历史 K 线
# datacenter 报表（基本面/分红，当前仅 A 股）；公告中心
_DATACENTER = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
_DATACENTER_WEB = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_ANNOUNCE = "https://np-anotice-stock.eastmoney.com/api/security/ann"
_TIMEOUT = 10.0
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_CST = timezone(timedelta(hours=8))  # 数据时间统一以北京时间呈现

# 实时快照字段（东财 f-code）：价格类按 f59 小数位缩放，比率类恒 ÷100
_QUOTE_FIELDS = "f43,f44,f45,f46,f47,f48,f50,f57,f58,f59,f60,f86,f116,f117,f162,f167,f168,f169,f170,f171"
# K 线 fields2：日期/开/收/高/低/量/额/涨跌幅（接口已返回小数，无需缩放）
_KLINE_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58"

_PERIOD = {
    "daily": "101", "weekly": "102", "monthly": "103",
    "1min": "1", "5min": "5", "15min": "15", "30min": "30", "60min": "60",
}
_ADJUST = {"none": "0", "qfq": "1", "hfq": "2"}
_STOCK_CLASSIFY = {"AStock", "HK", "UsStock"}  # 东财 Classify 实值：A股 AStock / 港股 HK / 美股 UsStock


def _pct(v) -> float | None:
    # 比率/百分比字段恒 ÷100；东财用 0 表示该市场无此值（如港股/美股 PE）
    if not isinstance(v, (int, float)) or v == 0:
        return None
    return round(v / 100, 2)


def _num(v) -> float | None:
    return v if isinstance(v, (int, float)) else None


def _round2(v) -> float | None:
    return round(v, 2) if isinstance(v, (int, float)) else None


def _date(v) -> str:
    # datacenter / 公告接口返回 "YYYY-MM-DD HH:mm:ss"，对外只保留日期
    return v[:10] if isinstance(v, str) and len(v) >= 10 else ""


def _a_share_code(secid: str, market: str) -> str:
    """基本面/公告/分红当前仅 A 股（datacenter F10 报表为 A 股口径）。返回纯数字代码。"""
    prefix, _, code = secid.partition(".")
    if prefix not in ("0", "1"):
        raise ValueError(
            f"{market or '该标的'}暂不支持基本面/公告/分红查询（当前仅 A 股，港股/美股待后续接入）"
        )
    return code


def _fmt_ts(ts) -> str:
    if not isinstance(ts, (int, float)) or ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, _CST).strftime("%Y-%m-%d %H:%M:%S")


async def _resolve(symbol: str) -> tuple[str, str, str]:
    """代码/名称/美股 ticker → (secid, 名称, 市场标签)。市场判断由东财完成。"""
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(_SUGGEST, params={"input": symbol, "type": "14", "count": "8"})
    resp.raise_for_status()
    data = (resp.json().get("QuotationCodeTable") or {}).get("Data") or []
    stocks = [d for d in data if d.get("Classify") in _STOCK_CLASSIFY]
    pool = stocks or data
    if not pool:
        raise ValueError(f"未找到标的: {symbol}")
    # 裸代码可能跨市场撞号（如港股 00700 与深A 000700），精确代码匹配优先于东财默认排序
    key = symbol.strip().upper()
    exact = [d for d in pool if (d.get("Code") or "").upper() == key]
    d = (exact or pool)[0]
    secid = d.get("QuoteID")
    if not secid or "." not in secid:
        raise ValueError(f"无法解析标的: {symbol}")
    return secid, d.get("Name") or symbol, d.get("SecurityTypeName") or ""


async def get_quote(symbol: str) -> StockQuote:
    secid, name, market = await _resolve(symbol)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(_QUOTE, params={"secid": secid, "fields": _QUOTE_FIELDS})
    resp.raise_for_status()
    d = resp.json().get("data")
    if not d:
        raise ValueError(f"未获取到行情: {symbol}")
    dec = d.get("f59") if isinstance(d.get("f59"), int) else 2

    def price(key) -> float | None:
        v = d.get(key)
        return round(v / 10 ** dec, dec) if isinstance(v, (int, float)) else None

    return StockQuote(
        symbol=d.get("f57") or symbol,
        name=name or d.get("f58") or symbol,
        market=market,
        price=price("f43"),
        change=price("f169"),
        change_pct=_pct(d.get("f170")) or 0.0,
        open=price("f46"),
        high=price("f44"),
        low=price("f45"),
        prev_close=price("f60"),
        amplitude_pct=_pct(d.get("f171")),
        turnover_pct=_pct(d.get("f168")),
        volume=_num(d.get("f47")) or 0.0,
        amount=_num(d.get("f48")) or 0.0,
        volume_ratio=_pct(d.get("f50")),
        pe=_pct(d.get("f162")),
        pb=_pct(d.get("f167")),
        market_cap=_num(d.get("f116")),
        float_market_cap=_num(d.get("f117")),
        updated_at=_fmt_ts(d.get("f86")),
    )


def _ma(closes: list[float], n: int) -> float | None:
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 3)


async def get_history(
    symbol: str, start_date: str, end_date: str, period: str = "daily", adjust: str = "qfq"
) -> StockHistory:
    if start_date > end_date:
        raise ValueError(f"起始日期 {start_date} 晚于结束日期 {end_date}")
    klt = _PERIOD.get(period)
    if klt is None:
        raise ValueError(f"不支持的周期: {period}（可选 daily/weekly/monthly/1min/5min/15min/30min/60min）")
    fqt = _ADJUST.get(adjust)
    if fqt is None:
        raise ValueError(f"不支持的复权方式: {adjust}（可选 qfq/hfq/none）")
    secid, name, market = await _resolve(symbol)
    params = {
        "secid": secid, "klt": klt, "fqt": fqt,
        "beg": start_date.replace("-", ""), "end": end_date.replace("-", ""),
        "fields1": "f1,f2,f3", "fields2": _KLINE_FIELDS2, "lmt": "100000",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(_KLINE, params=params)
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    klines = data.get("klines")
    if not klines:
        raise ValueError(f"区间 {start_date}..{end_date} 无 {symbol} 的 K 线数据")
    points = []
    for line in klines:
        p = line.split(",")
        points.append(KlinePoint(
            date=p[0], open=float(p[1]), close=float(p[2]), high=float(p[3]),
            low=float(p[4]), volume=float(p[5]), amount=float(p[6]), change_pct=float(p[7]),
        ))
    closes = [p.close for p in points]
    start_close, end_close = closes[0], closes[-1]
    peak = closes[0]
    mdd = 0.0
    for c in closes:
        peak = max(peak, c)
        if peak > 0:
            mdd = min(mdd, (c - peak) / peak)
    return StockHistory(
        symbol=data.get("code") or symbol,
        name=data.get("name") or name,
        market=market,
        period=period,
        adjust=adjust,
        points=points,
        start_close=start_close,
        end_close=end_close,
        high=max(p.high for p in points),
        low=min(p.low for p in points),
        change_pct=round((end_close - start_close) / start_close * 100, 2) if start_close else 0.0,
        max_drawdown_pct=round(mdd * 100, 2),
        ma={"ma5": _ma(closes, 5), "ma10": _ma(closes, 10), "ma20": _ma(closes, 20)},
    )


async def _datacenter(base: str, report: str, columns: str, filter_expr: str,
                      page_size: int, sort: str = "REPORT_DATE") -> list[dict]:
    params = {
        "reportName": report, "columns": columns, "filter": filter_expr,
        "pageSize": str(page_size), "sortColumns": sort, "sortTypes": "-1",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(base, params=params)
    resp.raise_for_status()
    return ((resp.json().get("result") or {}).get("data")) or []


def _market_kind(secid: str) -> str:
    p = secid.partition(".")[0]
    if p in ("0", "1"):
        return "A"
    if p == "116":
        return "HK"
    if p in ("105", "106", "107"):
        return "US"
    return "OTHER"


_US_SUFFIX = {"105": "O", "106": "N", "107": "A"}


def _build_a(r: dict) -> FinancialIndicator:
    return FinancialIndicator(
        report=r.get("REPORT_DATE_NAME") or "",
        report_type=r.get("REPORT_TYPE") or "",
        notice_date=_date(r.get("NOTICE_DATE")),
        revenue=_num(r.get("TOTALOPERATEREVE")),
        revenue_yoy=_round2(r.get("TOTALOPERATEREVETZ")),
        net_profit=_num(r.get("PARENTNETPROFIT")),
        net_profit_yoy=_round2(r.get("PARENTNETPROFITTZ")),
        net_profit_excl=_num(r.get("KCFJCXSYJLR")),
        eps=_num(r.get("EPSJB")),
        bps=_round2(r.get("BPS")),
        roe=_round2(r.get("ROEJQ")),
        net_margin=_round2(r.get("XSJLL")),
        gross_margin=_round2(r.get("XSMLL")),
        debt_ratio=_round2(r.get("ZCFZL")),
    )


def _build_hk(r: dict) -> FinancialIndicator:
    return FinancialIndicator(
        report=r.get("REPORT_TYPE") or "",
        report_type=r.get("REPORT_TYPE") or "",
        notice_date=_date(r.get("REPORT_DATE")),
        revenue=_num(r.get("OPERATE_INCOME")),
        revenue_yoy=_round2(r.get("OPERATE_INCOME_YOY")),
        net_profit=_num(r.get("HOLDER_PROFIT")),
        net_profit_yoy=_round2(r.get("HOLDER_PROFIT_YOY")),
        eps=_num(r.get("BASIC_EPS")),
        bps=_round2(r.get("BPS")),
        roe=_round2(r.get("ROE_AVG")),
        net_margin=_round2(r.get("NET_PROFIT_RATIO")),
        gross_margin=_round2(r.get("GROSS_PROFIT_RATIO")),
        debt_ratio=_round2(r.get("DEBT_ASSET_RATIO")),
    )


# 美股利润表为逐项长表，取累计口径（一/中/三季报 + 年报，排除单季报）后按报告期聚合
_US_CUM_DTC = {"001", "002", "003", "004"}
_US_ITEM_REVENUE = "004001999"
_US_ITEM_GROSS = "004005999"
_US_ITEM_NET = "004015999"
_US_ITEM_NET_ALT = "004013999"
_US_ITEM_EPS = "004017003"


def _build_us(rows: list[dict], periods: int) -> list[FinancialIndicator]:
    grouped: dict[str, dict] = {}
    order: list[str] = []
    for r in rows:
        if str(r.get("DATE_TYPE_CODE")) not in _US_CUM_DTC:
            continue
        dt = r.get("REPORT_DATE")
        if dt not in grouped:
            grouped[dt] = {"meta": r, "items": {}}
            order.append(dt)
        grouped[dt]["items"][r.get("STD_ITEM_CODE")] = (r.get("AMOUNT"), r.get("YOY_RATIO"))
    out = []
    for dt in order[:periods]:
        items = grouped[dt]["items"]
        meta = grouped[dt]["meta"]
        rev, rev_yoy = items.get(_US_ITEM_REVENUE, (None, None))
        net, net_yoy = items.get(_US_ITEM_NET) or items.get(_US_ITEM_NET_ALT) or (None, None)
        gross = items.get(_US_ITEM_GROSS, (None, None))[0]
        eps = items.get(_US_ITEM_EPS, (None, None))[0]
        revenue, net_profit, gross_profit = _num(rev), _num(net), _num(gross)
        out.append(FinancialIndicator(
            report=(meta.get("REPORT_TYPE_DETAILS") or "").replace(" ", ""),
            report_type=meta.get("REPORT_TYPE") or "",
            notice_date="",
            revenue=revenue,
            revenue_yoy=_round2(rev_yoy),
            net_profit=net_profit,
            net_profit_yoy=_round2(net_yoy),
            eps=_num(eps),
            gross_margin=round(gross_profit / revenue * 100, 2) if gross_profit and revenue else None,
            net_margin=round(net_profit / revenue * 100, 2) if net_profit and revenue else None,
        ))
    return out


_FUND_COLS_A = (
    "REPORT_DATE_NAME,REPORT_TYPE,NOTICE_DATE,CURRENCY,EPSJB,BPS,TOTALOPERATEREVE,"
    "PARENTNETPROFIT,KCFJCXSYJLR,TOTALOPERATEREVETZ,PARENTNETPROFITTZ,ROEJQ,XSJLL,XSMLL,ZCFZL"
)
_FUND_COLS_HK = (
    "REPORT_TYPE,REPORT_DATE,CURRENCY,OPERATE_INCOME,OPERATE_INCOME_YOY,HOLDER_PROFIT,"
    "HOLDER_PROFIT_YOY,BASIC_EPS,BPS,ROE_AVG,NET_PROFIT_RATIO,GROSS_PROFIT_RATIO,DEBT_ASSET_RATIO"
)


async def get_fundamentals(symbol: str, periods: int = 8) -> StockFundamentals:
    """主要财务指标。A股全字段；港股同等丰富；美股取利润表累计口径（营收/净利及同比、EPS、
    毛利率/净利率），ROE/每股净资产/资产负债率美股暂为 null（需资产负债表，后续补）。"""
    secid, name, market = await _resolve(symbol)
    kind = _market_kind(secid)
    code = secid.partition(".")[2]
    currency = "CNY"
    if kind == "A":
        rows = await _datacenter(_DATACENTER, "RPT_F10_FINANCE_MAINFINADATA",
                                 _FUND_COLS_A, f'(SECURITY_CODE="{code}")', periods)
        indicators = [_build_a(r) for r in rows]
        currency = (rows[0].get("CURRENCY") if rows else None) or "CNY"
    elif kind == "HK":
        rows = await _datacenter(_DATACENTER, "RPT_HKF10_FN_MAININDICATOR", _FUND_COLS_HK,
                                 f'(SECUCODE="{code}.HK")', periods, sort="STD_REPORT_DATE")
        indicators = [_build_hk(r) for r in rows]
        currency = (rows[0].get("CURRENCY") if rows else None) or "HKD"
    elif kind == "US":
        secucode = f"{code}.{_US_SUFFIX.get(secid.partition('.')[0], 'O')}"
        rows = await _datacenter(_DATACENTER, "RPT_USF10_FN_INCOME", "ALL",
                                 f'(SECUCODE="{secucode}")', periods * 80, sort="STD_REPORT_DATE")
        indicators = _build_us(rows, periods)
        currency = (rows[0].get("CURRENCY_ABBR") if rows else None) or "USD"
    else:
        raise ValueError(f"{market or '该标的'}暂不支持基本面查询")
    if not indicators:
        raise ValueError(f"未获取到 {symbol} 的财务指标")
    return StockFundamentals(symbol=code, name=name, market=market,
                             currency=currency, periods=indicators)


async def get_announcements(symbol: str, limit: int = 10) -> StockAnnouncements:
    secid, name, market = await _resolve(symbol)
    code = _a_share_code(secid, market)
    params = {
        "sr": "-1", "page_size": str(limit), "page_index": "1",
        "ann_type": "A", "stock_list": code,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(_ANNOUNCE, params=params)
    resp.raise_for_status()
    items = ((resp.json().get("data") or {}).get("list")) or []
    anns = [
        Announcement(
            date=_date(it.get("notice_date")),
            type=(it.get("columns") or [{}])[0].get("column_name") or "",
            title=it.get("title_ch") or it.get("title") or "",
        )
        for it in items
    ]
    return StockAnnouncements(symbol=code, name=name, market=market, announcements=anns)


_DIV_COLS = (
    "REPORT_DATE,PLAN_NOTICE_DATE,EQUITY_RECORD_DATE,EX_DIVIDEND_DATE,"
    "IMPL_PLAN_PROFILE,ASSIGN_PROGRESS,PRETAX_BONUS_RMB"
)


async def get_dividends(symbol: str, limit: int = 10) -> StockDividends:
    secid, name, market = await _resolve(symbol)
    code = _a_share_code(secid, market)
    rows = await _datacenter(_DATACENTER_WEB, "RPT_SHAREBONUS_DET", _DIV_COLS,
                             f'(SECURITY_CODE="{code}")', limit)
    records = [
        DividendRecord(
            report=_date(r.get("REPORT_DATE")),
            notice_date=_date(r.get("PLAN_NOTICE_DATE")),
            plan=r.get("IMPL_PLAN_PROFILE") or None,
            progress=r.get("ASSIGN_PROGRESS") or None,
            pretax_cash_per10=_num(r.get("PRETAX_BONUS_RMB")),
            ex_dividend_date=_date(r.get("EX_DIVIDEND_DATE")) or None,
        )
        for r in rows
    ]
    return StockDividends(symbol=code, name=name, market=market, dividends=records)
