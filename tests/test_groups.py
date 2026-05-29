import pytest

from app.tools.groups import create_group, delete_group, list_groups, update_group


async def test_create_and_list():
    group = await create_group(name="家庭", role_ids=["r1", "r2"])
    listed = await list_groups()
    assert listed == [group]


async def test_update_replaces_role_ids():
    group = await create_group(name="原", role_ids=["r1"])
    updated = await update_group(group_id=group["id"], role_ids=["r2", "r3"])
    assert updated["role_ids"] == ["r2", "r3"]
    assert updated["name"] == "原"


async def test_update_missing_raises():
    with pytest.raises(ValueError):
        await update_group(group_id="missing", name="x")


async def test_delete_group():
    group = await create_group(name="临时")
    await delete_group(group_id=group["id"])
    assert await list_groups() == []

    with pytest.raises(ValueError):
        await delete_group(group_id=group["id"])
