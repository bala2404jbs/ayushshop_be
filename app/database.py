from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from .config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True  # Verifies connection is valid before usage
)

async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    # In serverless environments, avoid creating tables on startup to prevent timeouts.
    # Use Alembic migrations instead.
    pass
    # async with engine.begin() as conn:
    #     # await conn.run_sync(SQLModel.metadata.drop_all)
    #     await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
