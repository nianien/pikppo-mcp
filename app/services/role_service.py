import json
from app.database import get_db
from app.models.role import Role, RoleCreate, RoleUpdate


async def list_roles() -> list[Role]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM roles ORDER BY is_default DESC, created_at ASC")
    rows = await cursor.fetchall()
    return [Role(**dict(r), is_default=bool(r["is_default"])) for r in rows]


async def get_role(role_id: str) -> Role | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return Role(**dict(row), is_default=bool(row["is_default"]))


async def create_role(data: RoleCreate) -> Role:
    role = Role(**data.model_dump())
    db = await get_db()
    await db.execute(
        "INSERT INTO roles (id, name, icon, description, color, system_prompt, is_default, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
        (role.id, role.name, role.icon, role.description, role.color, role.system_prompt, role.created_at),
    )
    await db.commit()
    return role


async def update_role(role_id: str, data: RoleUpdate) -> Role | None:
    existing = await get_role(role_id)
    if not existing:
        return None
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [role_id]
    db = await get_db()
    await db.execute(f"UPDATE roles SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_role(role_id)


async def delete_role(role_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("SELECT is_default FROM roles WHERE id = ?", (role_id,))
    row = await cursor.fetchone()
    if not row:
        return False
    if row["is_default"]:
        return False
    await db.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    await db.commit()
    return True