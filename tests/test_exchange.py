import time

import pytest

from app.services import exchange_service
from app.tools.exchange import convert_currency, list_exchange_rates

_FAKE = {
    "result": "success",
    "base_code": "USD",
    "rates": {"USD": 1.0, "CNY": 7.2, "EUR": 0.92},
    "time_last_update_utc": "Tue, 16 Jun 2026 00:02:31 +0000",
}


@pytest.fixture
def fake_api(monkeypatch):
    async def _fake_fetch(base: str):
        if base.upper() != "USD":
            raise ValueError(f"汇率数据源返回失败（基准币种 {base} 可能无效）")
        return _FAKE
    monkeypatch.setattr(exchange_service, "_fetch", _fake_fetch)


async def test_convert_applies_rate_and_amount(fake_api):
    result = await convert_currency(from_currency="usd", to_currency="cny", amount=10)
    assert result["from_currency"] == "USD"
    assert result["to_currency"] == "CNY"
    assert result["rate"] == 7.2
    assert result["converted"] == 72.0


async def test_convert_default_amount_is_one(fake_api):
    result = await convert_currency(from_currency="USD", to_currency="EUR")
    assert result["amount"] == 1.0
    assert result["converted"] == 0.92


async def test_convert_unknown_target_raises(fake_api):
    with pytest.raises(ValueError):
        await convert_currency(from_currency="USD", to_currency="XXX")


async def test_list_rates_returns_table(fake_api):
    table = await list_exchange_rates(base="USD")
    assert table["base"] == "USD"
    assert table["rates"]["CNY"] == 7.2
    assert table["updated_at"]


async def test_invalid_base_raises(fake_api):
    with pytest.raises(ValueError):
        await list_exchange_rates(base="ZZZ")


async def test_fetch_caches_until_next_update(monkeypatch):
    # 缓存命中验证：同一 base 多次调用只打一次外部 API
    exchange_service._cache.clear()
    calls = {"n": 0}

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {**_FAKE, "time_next_update_unix": time.time() + 1000}

    class _FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url):
            calls["n"] += 1
            return _FakeResp()

    monkeypatch.setattr(exchange_service.httpx, "AsyncClient", _FakeClient)

    await exchange_service.convert("USD", "CNY", 1)
    await exchange_service.convert("USD", "EUR", 1)
    assert calls["n"] == 1  # 第二次走缓存
    exchange_service._cache.clear()
