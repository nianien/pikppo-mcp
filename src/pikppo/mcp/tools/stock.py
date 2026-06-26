from typing import Annotated

from pydantic import Field

from pikppo.mcp.server import mcp
from pikppo.mcp.services import stock_service

_SYMBOL_DESC = "股票代码、名称或美股代码，自动识别市场，如 600519 / 贵州茅台 / 00700 / AAPL"


@mcp.tool(
    name="get_stock_quote",
    title="股票实时行情",
    description="查询股票实时行情快照（A股/港股/美股），含最新价、涨跌幅、开高低收、成交量额、换手率、市盈率、市值等。行情通常有延迟，结果不构成投资建议",
)
async def get_stock_quote(
    symbol: Annotated[str, Field(description=_SYMBOL_DESC)],
) -> dict:
    quote = await stock_service.get_quote(symbol)
    return quote.model_dump()


@mcp.tool(
    name="get_stock_history",
    title="股票历史行情",
    description="查询股票历史 K 线（A股/港股/美股）并附区间统计（涨跌幅、最高/最低、5/10/20 日均线、最大回撤）。行情有延迟，结果不构成投资建议",
)
async def get_stock_history(
    symbol: Annotated[str, Field(description=_SYMBOL_DESC)],
    start_date: Annotated[str, Field(description="起始日期，格式 YYYY-MM-DD")],
    end_date: Annotated[str, Field(description="结束日期，格式 YYYY-MM-DD")],
    period: Annotated[str, Field(description="K 线周期：daily/weekly/monthly 或 1min/5min/15min/30min/60min")] = "daily",
    adjust: Annotated[str, Field(description="复权方式：qfq 前复权 / hfq 后复权 / none 不复权")] = "qfq",
) -> dict:
    history = await stock_service.get_history(symbol, start_date, end_date, period, adjust)
    return history.model_dump()


@mcp.tool(
    name="get_stock_fundamentals",
    title="股票基本面",
    description="查询股票主要财务指标（A股/港股/美股）：按报告期的营收、净利及同比、EPS、毛利率/净利率等；A股与港股另含 ROE、每股净资产、资产负债率（美股暂缺）。结果不构成投资建议",
)
async def get_stock_fundamentals(
    symbol: Annotated[str, Field(description=_SYMBOL_DESC)],
    periods: Annotated[int, Field(description="返回最近多少期报告，默认 8", ge=1, le=40)] = 8,
) -> dict:
    fundamentals = await stock_service.get_fundamentals(symbol, periods)
    return fundamentals.model_dump()


@mcp.tool(
    name="get_stock_announcements",
    title="股票公告",
    description="查询股票最新公告列表（当前仅 A 股），含标题、分类、日期，用于了解公司事件",
)
async def get_stock_announcements(
    symbol: Annotated[str, Field(description=_SYMBOL_DESC)],
    limit: Annotated[int, Field(description="返回条数，默认 10", ge=1, le=50)] = 10,
) -> dict:
    announcements = await stock_service.get_announcements(symbol, limit)
    return announcements.model_dump()


@mcp.tool(
    name="get_stock_dividends",
    title="股票分红送配",
    description="查询股票分红送配历史（当前仅 A 股），含方案描述、进度、每 10 股税前现金、除权除息日。结果不构成投资建议",
)
async def get_stock_dividends(
    symbol: Annotated[str, Field(description=_SYMBOL_DESC)],
    limit: Annotated[int, Field(description="返回条数，默认 10", ge=1, le=50)] = 10,
) -> dict:
    dividends = await stock_service.get_dividends(symbol, limit)
    return dividends.model_dump()
