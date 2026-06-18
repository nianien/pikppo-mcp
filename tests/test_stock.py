import pytest

from app.services import stock_service
from app.tools.stock import (
    get_stock_announcements,
    get_stock_dividends,
    get_stock_fundamentals,
    get_stock_history,
    get_stock_quote,
)

_SUGGEST_A = {"QuotationCodeTable": {"Data": [
    {"Code": "600519", "Name": "贵州茅台", "QuoteID": "1.600519",
     "Classify": "AStock", "SecurityTypeName": "沪A"},
]}}

# 茅台风格快照（原始放大整数，f59=2 → 价格 ÷100；比率字段 ÷100）
_QUOTE_A = {"data": {
    "f43": 122140, "f44": 123887, "f45": 122004, "f46": 123500, "f47": 30061,
    "f48": 3684002296.0, "f50": 152, "f57": "600519", "f58": "贵州茅台", "f59": 2,
    "f60": 124000, "f86": 1750000000, "f116": 1.5e12, "f117": 1.5e12,
    "f162": 1401, "f167": 564, "f168": 24, "f169": -1860, "f170": -150, "f171": 152,
}}

_KLINE = {"data": {"code": "600519", "name": "贵州茅台", "klines": [
    "2026-06-01,10,10,11,9,100,1000,0",
    "2026-06-02,10,12,13,10,100,1200,20",
    "2026-06-03,12,11,12,10,100,1100,-8.33",
]}}


def _fake_client(suggest=None, quote=None, kline=None, fundamentals=None,
                 announcements=None, dividends=None):
    class _Resp:
        def __init__(self, payload): self._p = payload
        def raise_for_status(self): pass
        def json(self): return self._p

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            if "suggest" in url:
                return _Resp(suggest)
            if "kline" in url:
                return _Resp(kline)
            if "anotice" in url:
                return _Resp(announcements)
            if "datacenter-web" in url:
                return _Resp(dividends)
            if "datacenter" in url:
                return _Resp(fundamentals)
            return _Resp(quote)
    return _Client


@pytest.fixture
def fake_quote(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, quote=_QUOTE_A))


async def test_quote_scaling_and_fields(fake_quote):
    q = await get_stock_quote(symbol="600519")
    assert q["symbol"] == "600519"
    assert q["name"] == "贵州茅台"
    assert q["market"] == "沪A"
    assert q["price"] == 1221.4  # 122140 / 100
    assert q["change"] == -18.6  # -1860 / 100
    assert q["change_pct"] == -1.5  # -150 / 100
    assert q["open"] == 1235.0 and q["high"] == 1238.87 and q["low"] == 1220.04
    assert q["prev_close"] == 1240.0
    assert q["turnover_pct"] == 0.24  # 24 / 100
    assert q["volume_ratio"] == 1.52  # 152 / 100
    assert q["pe"] == 14.01 and q["pb"] == 5.64
    assert q["volume"] == 30061 and q["amount"] == 3684002296.0
    assert q["updated_at"]  # f86 → 北京时间字符串


async def test_quote_zero_pe_becomes_null(monkeypatch):
    # 港股/美股该字段东财返回 0，应映射为 null 而非 0.0
    quote = {"data": {**_QUOTE_A["data"], "f162": 0}}
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, quote=quote))
    q = await get_stock_quote(symbol="600519")
    assert q["pe"] is None


async def test_unknown_symbol_raises(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest={"QuotationCodeTable": {"Data": []}}))
    with pytest.raises(ValueError):
        await get_stock_quote(symbol="不存在的标的")


@pytest.fixture
def fake_history(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, kline=_KLINE))


async def test_history_series_and_stats(fake_history):
    h = await get_stock_history(
        symbol="600519", start_date="2026-06-01", end_date="2026-06-03")
    assert [p["date"] for p in h["points"]] == ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert h["start_close"] == 10 and h["end_close"] == 11
    assert h["change_pct"] == 10.0  # (11-10)/10*100
    assert h["high"] == 13 and h["low"] == 9
    assert h["max_drawdown_pct"] == -8.33  # 12 → 11
    assert h["ma"] == {"ma5": None, "ma10": None, "ma20": None}  # 不足 5 根


async def test_history_inverted_range_raises(fake_history):
    with pytest.raises(ValueError):
        await get_stock_history(
            symbol="600519", start_date="2026-06-03", end_date="2026-06-01")


async def test_history_invalid_period_raises(fake_history):
    with pytest.raises(ValueError):
        await get_stock_history(
            symbol="600519", start_date="2026-06-01", end_date="2026-06-03", period="yearly")


async def test_history_empty_raises(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, kline={"data": {"klines": []}}))
    with pytest.raises(ValueError):
        await get_stock_history(
            symbol="600519", start_date="2026-06-01", end_date="2026-06-03")


_SUGGEST_HK = {"QuotationCodeTable": {"Data": [
    {"Code": "00700", "Name": "腾讯控股", "QuoteID": "116.00700",
     "Classify": "HKStock", "SecurityTypeName": "港股"},
]}}

_SUGGEST_US = {"QuotationCodeTable": {"Data": [
    {"Code": "AAPL", "Name": "苹果", "QuoteID": "105.AAPL",
     "Classify": "UsStock", "SecurityTypeName": "美股"},
]}}

_FUND_HK = {"result": {"data": [{
    "REPORT_TYPE": "2026年一季报", "REPORT_DATE": "2026-03-31 00:00:00", "CURRENCY": "HKD",
    "OPERATE_INCOME": 196458000000, "OPERATE_INCOME_YOY": 9.13,
    "HOLDER_PROFIT": 58093000000, "HOLDER_PROFIT_YOY": 21.48,
    "BASIC_EPS": 6.431, "BPS": 123.81, "ROE_AVG": 5.09,
    "NET_PROFIT_RATIO": 30.23, "GROSS_PROFIT_RATIO": 56.64, "DEBT_ASSET_RATIO": 40.94,
}]}}

# 美股利润表长表：累计口径(dtc 002)应被采用，单季(dtc 008)同期同项必须被排除
_FUND_US = {"result": {"data": [
    {"REPORT_DATE": "2026-03-28 00:00:00", "REPORT_TYPE": "累计季报",
     "REPORT_TYPE_DETAILS": "2026年 中报", "DATE_TYPE_CODE": "002", "CURRENCY_ABBR": "USD",
     "STD_ITEM_CODE": "004001999", "AMOUNT": 254940000000, "YOY_RATIO": 16.06},
    {"REPORT_DATE": "2026-03-28 00:00:00", "DATE_TYPE_CODE": "002",
     "STD_ITEM_CODE": "004015999", "AMOUNT": 71687000000, "YOY_RATIO": 17.29},
    {"REPORT_DATE": "2026-03-28 00:00:00", "DATE_TYPE_CODE": "002",
     "STD_ITEM_CODE": "004005999", "AMOUNT": 124000000000, "YOY_RATIO": 0},
    {"REPORT_DATE": "2026-03-28 00:00:00", "DATE_TYPE_CODE": "002",
     "STD_ITEM_CODE": "004017003", "AMOUNT": 4.87, "YOY_RATIO": 0},
    {"REPORT_DATE": "2026-03-28 00:00:00", "DATE_TYPE_CODE": "008",
     "STD_ITEM_CODE": "004001999", "AMOUNT": 111184000000, "YOY_RATIO": 16.59},
]}}

_FUND = {"result": {"data": [{
    "REPORT_DATE_NAME": "2026一季报", "REPORT_TYPE": "一季报",
    "NOTICE_DATE": "2026-04-25 00:00:00", "CURRENCY": "CNY",
    "EPSJB": 21.76, "BPS": 216.32, "TOTALOPERATEREVE": 54702912385.23,
    "PARENTNETPROFIT": 27242512886.45, "KCFJCXSYJLR": 27239985194.41,
    "TOTALOPERATEREVETZ": 6.336, "PARENTNETPROFITTZ": 1.4714,
    "ROEJQ": 10.57, "XSJLL": 52.224, "XSMLL": 89.759, "ZCFZL": 12.1227,
}]}}

_ANN = {"data": {"list": [{
    "notice_date": "2026-06-12 00:00:00",
    "columns": [{"column_name": "高管人员任职变动"}],
    "title_ch": "贵州茅台:关于聘任董事会秘书的公告", "title": "fallback",
}]}}

_DIV = {"result": {"data": [{
    "REPORT_DATE": "2025-12-31 00:00:00", "PLAN_NOTICE_DATE": "2026-04-17 00:00:00",
    "EQUITY_RECORD_DATE": None, "EX_DIVIDEND_DATE": None,
    "IMPL_PLAN_PROFILE": "10派280.2423元(含税)", "ASSIGN_PROGRESS": "股东大会决议通过",
    "PRETAX_BONUS_RMB": 280.2423,
}]}}


async def test_fundamentals_parse_and_round(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, fundamentals=_FUND))
    f = await get_stock_fundamentals(symbol="600519")
    assert f["symbol"] == "600519" and f["currency"] == "CNY"
    p = f["periods"][0]
    assert p["report"] == "2026一季报"
    assert p["notice_date"] == "2026-04-25"
    assert p["revenue"] == 54702912385.23  # 原值不缩放
    assert p["revenue_yoy"] == 6.34 and p["net_profit_yoy"] == 1.47
    assert p["eps"] == 21.76 and p["roe"] == 10.57
    assert p["gross_margin"] == 89.76 and p["debt_ratio"] == 12.12


async def test_fundamentals_hk_parse(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_HK, fundamentals=_FUND_HK))
    f = await get_stock_fundamentals(symbol="00700")
    assert f["market"] == "港股" and f["currency"] == "HKD"
    p = f["periods"][0]
    assert p["revenue"] == 196458000000 and p["revenue_yoy"] == 9.13
    assert p["net_profit"] == 58093000000 and p["net_profit_yoy"] == 21.48
    assert p["eps"] == 6.431 and p["roe"] == 5.09
    assert p["gross_margin"] == 56.64 and p["debt_ratio"] == 40.94


async def test_fundamentals_us_uses_cumulative_basis(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_US, fundamentals=_FUND_US))
    f = await get_stock_fundamentals(symbol="AAPL")
    assert f["market"] == "美股" and f["currency"] == "USD"
    assert len(f["periods"]) == 1
    p = f["periods"][0]
    assert p["report"] == "2026年中报"
    assert p["revenue"] == 254940000000  # 累计口径，非单季 111184000000
    assert p["net_profit"] == 71687000000 and p["eps"] == 4.87
    assert p["gross_margin"] == 48.64  # 124000000000 / 254940000000
    assert p["net_margin"] == 28.12  # 71687000000 / 254940000000
    assert p["roe"] is None and p["debt_ratio"] is None  # 美股暂缺


async def test_announcements_non_a_share_raises(monkeypatch):
    # 公告/分红仍仅 A 股，港股/美股应给清晰报错
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_HK))
    with pytest.raises(ValueError):
        await get_stock_announcements(symbol="00700")


async def test_announcements_parse(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, announcements=_ANN))
    a = await get_stock_announcements(symbol="600519", limit=5)
    assert len(a["announcements"]) == 1
    an = a["announcements"][0]
    assert an["date"] == "2026-06-12"
    assert an["type"] == "高管人员任职变动"
    assert an["title"].startswith("贵州茅台")


async def test_dividends_parse(monkeypatch):
    monkeypatch.setattr(stock_service.httpx, "AsyncClient",
                        _fake_client(suggest=_SUGGEST_A, dividends=_DIV))
    d = await get_stock_dividends(symbol="600519")
    rec = d["dividends"][0]
    assert rec["report"] == "2025-12-31"
    assert rec["progress"] == "股东大会决议通过"
    assert rec["pretax_cash_per10"] == 280.2423
    assert rec["ex_dividend_date"] is None
    assert "10派" in rec["plan"]
