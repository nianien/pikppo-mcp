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


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    rate: float


class TrendResult(BaseModel):
    from_currency: str
    to_currency: str
    start_date: str
    end_date: str
    points: list[TrendPoint]  # 按日期升序的每日汇率（数据源仅工作日，周末/节假日无点）
    start_rate: float  # 区间首个有效汇率
    end_rate: float  # 区间末个有效汇率
    min_rate: float
    max_rate: float
    change_pct: float  # (end_rate - start_rate) / start_rate * 100，保留两位
