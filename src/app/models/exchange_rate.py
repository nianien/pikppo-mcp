from pydantic import BaseModel


class ConversionResult(BaseModel):
    from_currency: str
    to_currency: str
    rate: float  # 1 单位 from_currency 兑换的 to_currency
    amount: float  # 待换算金额
    converted: float  # 换算结果 = amount * rate
    updated_at: str  # 汇率数据更新时间（UTC）


class RateTable(BaseModel):
    base: str
    rates: dict[str, float]  # 1 单位 base 对各币种的汇率
    updated_at: str
