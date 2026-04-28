import json
from app.database import get_db
from app.models.group import Group, GroupCreate, GroupUpdate


async def list_groups() -> list[Group]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM groups")
    rows = await cursor.fetchall()
    return [Group(**dict(r), role_ids=json.loads(r["role_ids"])) for r in rows]


async def get_group(group_id: str) -> Group | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return Group(**dict(row), role_ids=json.loads(row["role_ids"]))


async def create_group(data: GroupCreate) -> Group:
    group = Group(**data.model_dump())
    db = await get_db()
    await db.execute(
        "INSERT INTO groups (id, name, role_ids) VALUES (?, ?, ?)",
        (group.id, group.name, json.dumps(group.role_ids)),
    )
    await db.commit()
    return group


async def update_group(group_id: str, data: GroupUpdate) -> Group | None:
    existing = await get_group(group_id)
    if not existing:
        return None
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    if "role_ids" in updates:
        updates["role_ids"] = json.dumps(updates["role_ids"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [group_id]
    db = await get_db()
    await db.execute(f"UPDATE groups SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_group(group_id)


async def delete_group(group_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM groups WHERE id = ? RETURNING id", (group_id,))
    row = await cursor.fetchone()
    await db.commit()
    return row is not None