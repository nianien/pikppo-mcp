from app.database import get_db
from app.models.user import UserProfile, UserProfileUpdate


async def get_profile() -> UserProfile:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM user_profile WHERE id = 1")
    row = await cursor.fetchone()
    return UserProfile(**dict(row))


async def update_profile(data: UserProfileUpdate) -> UserProfile:
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return await get_profile()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    db = await get_db()
    await db.execute(f"UPDATE user_profile SET {set_clause} WHERE id = 1", values)
    await db.commit()
    return await get_profile()