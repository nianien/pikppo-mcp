from app.server import mcp
from app.services import exchange_service


@mcp.tool()
async def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float = 1.0,
) -> dict:
    """按实时汇率换算货币金额

    Args:
        from_currency: 源币种 ISO 4217 代码，如 USD、CNY、EUR
        to_currency: 目标币种 ISO 4217 代码
        amount: 待换算金额，默认 1
    """
    result = await exchange_service.convert(from_currency, to_currency, amount)
    return result.model_dump()


@mcp.tool()
async def list_exchange_rates(base: str) -> dict:
    """查询某币种对一篮子货币的实时汇率表

    Args:
        base: 基准币种 ISO 4217 代码，如 USD、CNY、EUR
    """
    table = await exchange_service.get_rate_table(base)
    return table.model_dump()


@mcp.tool()
async def get_exchange_trend(
    from_currency: str,
    to_currency: str,
    start_date: str,
    end_date: str,
) -> dict:
    """查询一段日期区间内两币种的每日汇率走势，含起止值、最高/最低与涨跌幅

    数据为工作日汇率（周末/节假日无数据点），适合绘制趋势图或描述涨跌。

    Args:
        from_currency: 源币种 ISO 4217 代码，如 USD、CNY、EUR
        to_currency: 目标币种 ISO 4217 代码
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
    """
    trend = await exchange_service.get_trend(from_currency, to_currency, start_date, end_date)
    return trend.model_dump()
