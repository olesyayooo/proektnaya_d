from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from src.configs import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
new_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with new_session() as session:
        yield session
    
SessionDep = Annotated[AsyncSession, Depends(get_db)]

Base = declarative_base()
