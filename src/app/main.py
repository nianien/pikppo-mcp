from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db, close_db
from app.routers import roles, calendar, memories, groups, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="pikppo-api", lifespan=lifespan)

app.include_router(roles.router)
app.include_router(calendar.router)
app.include_router(memories.router)
app.include_router(groups.router)
app.include_router(users.router)
