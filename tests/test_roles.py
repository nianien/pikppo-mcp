import pytest

from app.tools.roles import create_role, delete_role, list_roles, update_role


async def test_create_then_list_roundtrip():
    role = await create_role(name="职场助理", icon="💼", description="工作", color=42, system_prompt="你是助理")
    assert role["id"]
    assert role["name"] == "职场助理"
    assert role["is_default"] is False

    roles = await list_roles()
    assert [r["id"] for r in roles] == [role["id"]]


async def test_update_modifies_fields_and_persists():
    role = await create_role(name="原名")
    updated = await update_role(role_id=role["id"], name="新名", icon="🚀")
    assert updated["name"] == "新名"
    assert updated["icon"] == "🚀"

    refetched = (await list_roles())[0]
    assert refetched["name"] == "新名"


async def test_update_missing_role_raises():
    with pytest.raises(ValueError):
        await update_role(role_id="does-not-exist", name="x")


async def test_delete_removes_role():
    role = await create_role(name="临时")
    await delete_role(role_id=role["id"])
    assert await list_roles() == []


async def test_delete_missing_role_raises():
    with pytest.raises(ValueError):
        await delete_role(role_id="does-not-exist")
