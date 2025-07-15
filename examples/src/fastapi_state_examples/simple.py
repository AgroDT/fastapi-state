"""Simple example of using fastapi-state."""

from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, status

from fastapi_state import state


def main() -> None:
    uvicorn.run(f'{__name__}:app')


type Database = dict[str, Any]


@state
def database() -> Database:
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    await database.inject(app)
    yield


DatabaseDep = Annotated[Database, Depends(database.extract)]

app = FastAPI(lifespan=lifespan)


@app.put('/{key}')
async def put_item(key: str, value: Annotated[Any, Body()], db: DatabaseDep) -> Any:  # noqa: ANN401
    db[key] = value
    return value


@app.get('/{key}')
async def get_item(key: str, db: DatabaseDep) -> Any:  # noqa: ANN401
    if key in db:
        return db[key]

    raise HTTPException(status.HTTP_404_NOT_FOUND)
