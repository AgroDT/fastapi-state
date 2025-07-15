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
async def test_duplicate_name(app: FastAPI, dict_state: State[..., dict[str, str]]) -> None:
    with pytest.raises(DuplicateStateNameError):
        await dict_state.inject(app)
