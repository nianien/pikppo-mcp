import pytest

from app.tools.memories import (
    clear_memories,
    create_memory,
    delete_memory,
    list_memories,
    update_memory,
)


async def test_create_and_list_orders_by_recency():
    first = await create_memory(type="semantic", content="第一条")
    second = await create_memory(type="semantic", content="第二条")

    memories = await list_memories()
    assert [m["id"] for m in memories[:2]] == [second["id"], first["id"]]


async def test_list_filters_by_type():
    sem = await create_memory(type="semantic", content="语义")
    await create_memory(type="episodic", content="情景")

    semantic_only = await list_memories(type="semantic")
    assert [m["id"] for m in semantic_only] == [sem["id"]]


async def test_list_filters_by_tags_with_intersection():
    a = await create_memory(type="semantic", content="A", tags=["健康", "饮食"])
    b = await create_memory(type="semantic", content="B", tags=["工作"])
    await create_memory(type="semantic", content="C", tags=["娱乐"])

    matched = await list_memories(tags=["健康", "工作"])
    assert {m["id"] for m in matched} == {a["id"], b["id"]}


async def test_update_replaces_tags():
    memory = await create_memory(type="semantic", content="X", tags=["旧"])
    updated = await update_memory(memory_id=memory["id"], tags=["新", "另一个"])
    assert updated["tags"] == ["新", "另一个"]


async def test_update_missing_raises():
    with pytest.raises(ValueError):
        await update_memory(memory_id="missing", content="x")


async def test_delete_and_clear():
    a = await create_memory(type="semantic", content="A")
    b = await create_memory(type="semantic", content="B")

    await delete_memory(memory_id=a["id"])
    remaining = await list_memories()
    assert [m["id"] for m in remaining] == [b["id"]]

    result = await clear_memories()
    assert "1" in result
    assert await list_memories() == []
