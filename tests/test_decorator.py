from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_state import DuplicateStateNameError, State


@pytest.mark.parametrize(
    ('url', 'text'),
    [pytest.param('/key', '"value"', id='db'), pytest.param('/const', '42', id='async-const')],
)
def test_get(client: TestClient, url: str, text: str) -> None:
    res = client.get(url)
    assert res.text == text


def test_ws(client: TestClient) -> None:
    session = client.websocket_connect('/const/ws')
    with session:
        msg = session.receive_text()
        assert msg == '42'


@pytest.mark.anyio
async def test_duplicate_name(dict_state: State[..., dict[str, str]]) -> None:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state: dict = {}
        await dict_state.inject(state)
        await dict_state.inject(state)
        yield state

    app = FastAPI(lifespan=lifespan)

    with pytest.raises(DuplicateStateNameError), TestClient(app):
        pass
