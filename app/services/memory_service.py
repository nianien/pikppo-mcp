import json
from app.database import get_db
from app.models.memory import Memory, MemoryCreate, MemoryUpdate, MemoryType


async def list_memories(
    type: MemoryType | None = None,
    tags: list[str] | None = None,
) -> list[Memory]:
    db = await get_db()
    query = "SELECT * FROM memories"
    params: list = []
    conditions = []
    if type:
        conditions.append("type = ?")
        params.append(type.value)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"])
        if tags and not set(tags).intersection(d["tags"]):
            continue
        results.append(Memory(**d))
    return results


async def get_memory(memory_id: str) -> Memory | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    return Memory(**d)


async def create_memory(data: MemoryCreate) -> Memory:
    memory = Memory(**data.model_dump())
    db = await get_db()
    await db.execute(
        "INSERT INTO memories (id, type, content, role_id, tags, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (memory.id, memory.type.value, memory.content, memory.role_id, json.dumps(memory.tags), memory.timestamp),
    )
    await db.commit()
    return memory


async def update_memory(memory_id: str, data: MemoryUpdate) -> Memory | None:
    existing = await get_memory(memory_id)
    if not existing:
        return None
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"])
    if "type" in updates:
        updates["type"] = updates["type"].value
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [memory_id]
    db = await get_db()
    await db.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_memory(memory_id)


async def delete_memory(memory_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM memories WHERE id = ? RETURNING id", (memory_id,))
    row = await cursor.fetchone()
    await db.commit()
    return row is not None


async def clear_memories() -> int:
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM memories")
    row = await cursor.fetchone()
    count = row["cnt"]
    await db.execute("DELETE FROM memories")
    await db.commit()
    return count