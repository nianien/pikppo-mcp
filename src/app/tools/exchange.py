from typing import Annotated

from pydantic import Field

from app.server import mcp
from app.services import exchange_service


@mcp.tool(
    name="convert_currency",
    title="货币换算",
    description="按实时汇率换算货币金额",
)
async def convert_currency(
    from_currency: Annotated[str, Field(description="源币种 ISO 4217 代码，如 USD、CNY、EUR")],
    to_currency: Annotated[str, Field(description="目标币种 ISO 4217 代码")],
    amount: Annotated[float, Field(description="待换算金额，默认 1")] = 1.0,
) -> dict:
    result = await exchange_service.convert(from_currency, to_currency, amount)
    return result.model_dump()


@mcp.tool(
    name="list_exchange_rates",
    title="实时汇率表",
    description="查询某币种对一篮子货币的实时汇率表",
)
async def list_exchange_rates(
    base: Annotated[str, Field(description="基准币种 ISO 4217 代码，如 USD、CNY、EUR")],
) -> dict:
    table = await exchange_service.get_rate_table(base)
    return table.model_dump()


@mcp.tool(
    name="get_exchange_trend",
    title="汇率走势",
    description="查询一段日期区间内两币种的每日汇率走势，含起止值、最高/最低与涨跌幅；数据为工作日汇率（周末/节假日无数据点）",
)
async def get_exchange_trend(
    from_currency: Annotated[str, Field(description="源币种 ISO 4217 代码，如 USD、CNY、EUR")],
    to_currency: Annotated[str, Field(description="目标币种 ISO 4217 代码")],
    start_date: Annotated[str, Field(description="起始日期，格式 YYYY-MM-DD")],
    end_date: Annotated[str, Field(description="结束日期，格式 YYYY-MM-DD")],
) -> dict:
    trend = await exchange_service.get_trend(from_currency, to_currency, start_date, end_date)
    return trend.model_dump()
