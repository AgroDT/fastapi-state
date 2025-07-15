"""Example of using fastapi-state for WebSocket chat."""

import pathlib
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Annotated
from urllib.parse import quote, unquote

import anyio
import uvicorn
from fastapi import (
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import HTMLResponse

from fastapi_state import state


def main() -> None:
    uvicorn.run(f'{__name__}:app')


@dataclass
class Chat:
    message_queue: anyio.create_memory_object_stream[dict] = field(
        default_factory=anyio.create_memory_object_stream[dict],
    )
    connections: list[WebSocket] = field(default_factory=list)

    async def connect(self, ws: WebSocket, user: str) -> None:
        await ws.accept()
        self.connections.append(ws)
        await self._broadcast({'user': user, 'message': 'Connected'})

        while True:
            msg = await ws.receive()
            if msg.get('type') == 'websocket.disconnect':
                self.connections.remove(ws)
                await self._broadcast({'user': user, 'message': 'Disconnected'})
                break


    async def run(self) -> None:
        while True:
            message = await self.message_queue[1].receive()
            await self._broadcast(message)

    async def _broadcast(self, message: dict) -> None:
        for ws in self.connections:
            with suppress(WebSocketDisconnect):
                await ws.send_json(message)


@state
def chat_state() -> Chat:
    return Chat()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    chat = await chat_state.inject(app)
    async with anyio.create_task_group() as tg:
        tg.start_soon(chat.run)
        yield
        tg.cancel_scope.cancel()
    for ws in chat.connections:
        await ws.close()


app = FastAPI(lifespan=lifespan)
index = HTMLResponse(pathlib.Path(__file__).joinpath('../chat.html').read_bytes())


def get_user(request: Request | WebSocket) -> str:
    if user := request.cookies.get('user'):
        return unquote(user)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED)


def get_user_http(request: Request) -> str:
    return get_user(request)


def get_user_ws(ws: WebSocket) -> str:
    return get_user(ws)


@app.get(path='/', operation_id='getIndex')
async def get_index() -> HTMLResponse:
    return index


@app.post(
    path='/login/{user}',
    operation_id='login',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def login(user: Annotated[str, Path(min_length=3)], response: Response) -> None:
    user = quote(user)
    response.set_cookie('user', user, secure=True, httponly=True, samesite='strict')


@app.post(
    path='/message',
    operation_id='postMessage',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def post_message(
    user: Annotated[str, Depends(get_user_http)],
    message: Annotated[str, Body(media_type='text/plain', min_length=3)],
    chat: Annotated[Chat, Depends(chat_state.extract)],
) -> None:
    await chat.message_queue[0].send({'user': user, 'message': message})


@app.websocket('/messages')
async def websocket_messages(
    ws: WebSocket,
    user: Annotated[str, Depends(get_user_ws)],
    chat: Annotated[Chat, Depends(chat_state.extract_ws)],
) -> None:
    await chat.connect(ws, user)
