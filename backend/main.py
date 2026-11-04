from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from src.database import engine, Base
from src.routers import router
import src.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    for i in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database is ready")
            break
        except Exception as e:
            print(f"Database is not ready yet ({i + 1}/10): {e}")
            await asyncio.sleep(2)
    else:
        raise RuntimeError("Could not connect to database")

    yield

app = FastAPI(
    lifespan=lifespan,
    servers=[{"url": "http://localhost:8000", "description": "Local"}],
    root_path="/api"
    )

origins = [
    "http://localhost:5173",
    "http://192.168.31.231:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
for route in app.routes:
    print(route.path)

"""
docker-compose up -d db
cd backend
source .venv/bin/activate
uvicorn main:app --reload
alembic revision --autogenerate -m ""
alembic upgrade head
"""