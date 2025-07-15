"""Example of using fastapi-state with SQLAlchemy."""

from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, status
from sqlalchemy import JSON, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fastapi_state import state


def main() -> None:
    uvicorn.run(f'{__name__}:app')


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = 'item'

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)


@state
async def database(url: str):  # noqa: ANN201
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    await database.inject(app, 'sqlite+aiosqlite://')
    yield


async def get_session(  # noqa: ANN201
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(database.extract)],
):
    async with session_maker() as session, session.begin():
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_session)]

app = FastAPI(lifespan=lifespan)


@app.put('/{key}')
async def put_item(key: str, value: Annotated[Any, Body()], db_session: DbSessionDep) -> Any:  # noqa: ANN401
    await db_session.execute(insert(Item).values(key=key, value=value))
    return value


@app.get('/{key}')
async def get_item(key: str, db_session: DbSessionDep) -> Any:  # noqa: ANN401
    item = await db_session.get(Item, key)

    if item:
        return item.value

    raise HTTPException(status.HTTP_404_NOT_FOUND)
