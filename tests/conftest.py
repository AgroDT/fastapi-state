from contextlib import asynccontextmanager
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient

from fastapi_state import State, state


type DictState = State[..., dict[str, str]]
type AsyncConstState = State[..., int]


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='session', name='client')
def test_client_fixture(app: FastAPI):
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope='session', name='app')
def app_fixture(dict_state: DictState, async_const_state: AsyncConstState) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await dict_state.inject(app)
        await async_const_state.inject(app)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get('/const')
    def get_const(const: Annotated[int, Depends(async_const_state.extract)]) -> int:
        return const

    @app.websocket('/const/ws')
    async def ws_const(
        ws: WebSocket,
        const: Annotated[int, Depends(async_const_state.extract_ws)],
    ) -> None:
        await ws.accept()
        await ws.send_json(const)
        await ws.close()

    @app.get('/{key}')
    def get_item(
        key: str,
        db: Annotated[dict[str, str], Depends(dict_state.extract)],
    ) -> str | None:
        return db.get(key)

    return app


@pytest.fixture(scope='session', name='dict_state')
def dict_database_fixture() -> DictState:
    @state
    def dict_state() -> dict[str, str]:
        return {'key': 'value'}

    return dict_state


@pytest.fixture(scope='session', name='async_const_state')
def async_constant_fixture() -> AsyncConstState:
    @state('custom-name')  # type: ignore[arg-type]
    async def async_const_state() -> int:
        return 42

    return async_const_state
