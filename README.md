# FastAPI State

Simple state management utilities for FastAPI applications.

This package provides a decorator-based approach to define and inject
custom application state objects. It supports both synchronous and
asynchronous state initializers and ensures that state keys are unique
within a FastAPI application's lifecycle.

## Features

- Define application-wide state using decorators
- Support for both sync and async state initializers
- Works with both HTTP and WebSocket routes.

## Limitations

- When using a custom name with `@state('...')`, mypy may require a
  `# type: ignore[arg-type]` comment due to type narrowing limitations.

## Installation

```sh
# Install with pip
pip install fastapi-state
# Or add to your project
uv add fastapi-state
```

## Example

See more usage [examples](./examples).

```python
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
```

## License

This project is licensed under the [MIT License](./LICENSE).
