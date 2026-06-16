import time

import httpx

from app.models.exchange_rate import ConversionResult, RateTable

# open.er-api.com：免费、无需 key，返回某基准币种对一篮子货币的汇率
_API_BASE = "https://open.er-api.com/v6/latest"
_TIMEOUT = 10.0

# 进程内缓存：base → (过期 unix 时间, 数据)。汇率天级更新，缓存到数据源声明的
# 下次更新时刻；同一对话内多次换算（同一 base）只打一次外部 API。
# stateless/scale-to-zero 下冷启动会丢缓存，回落到 API 调用，无副作用。
_cache: dict[str, tuple[float, dict]] = {}
_FALLBACK_TTL = 3600.0


async def _fetch(base: str) -> dict:
    base = base.upper()
    now = time.time()
    cached = _cache.get(base)
    if cached and cached[0] > now:
        return cached[1]
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{_API_BASE}/{base}")
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise ValueError(f"汇率数据源返回失败（基准币种 {base} 可能无效）")
    expires = data.get("time_next_update_unix") or (now + _FALLBACK_TTL)
    _cache[base] = (float(expires), data)
    return data


async def get_rate_table(base: str) -> RateTable:
    data = await _fetch(base)
    return RateTable(
        base=data["base_code"],
        rates=data["rates"],
        updated_at=data["time_last_update_utc"],
    )


async def convert(from_currency: str, to_currency: str, amount: float = 1.0) -> ConversionResult:
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    data = await _fetch(from_currency)
    rates = data["rates"]
    if to_currency not in rates:
        raise ValueError(f"不支持的目标币种: {to_currency}")
    rate = rates[to_currency]
    return ConversionResult(
        from_currency=from_currency,
        to_currency=to_currency,
        rate=rate,
        amount=amount,
        converted=round(amount * rate, 4),
        updated_at=data["time_last_update_utc"],
    )
