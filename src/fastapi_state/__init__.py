"""Simple state management utilities for FastAPI applications.

This package provides a decorator-based approach to define and inject
custom application state objects. It supports both synchronous and
asynchronous state initializers and ensures that state keys are unique
within a FastAPI application's lifecycle.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, overload

from fastapi import FastAPI, Request, WebSocket  # noqa: TC002


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    type StateInitializer[**P, R] = Callable[P, R | Awaitable[R]]

    type StateDecorator[**P, R] = Callable[[StateInitializer[P, R]], State[P, R]]


@overload
def state[**P, R](init_or_name: StateInitializer[P, R]) -> State[P, R]: ...
@overload
def state[**P, R](init_or_name: str) -> StateDecorator[P, R]: ...


def state[**P, R](
    init_or_name: StateInitializer[P, R] | str,
) -> State[P, R] | StateDecorator[P, R]:
    """Decorate a function to define FastAPI application state.

    Can be used in two forms:

    1. Register the state under the function's own name (used without parentheses).
    2. Register the state under a custom name (used with a string argument).

    The decorated function is called once and its result is stored
    in `app.state` under the given name. Supports both sync and async initializers.

    Notes:
        Mypy does not handle decorator closures well when used with a custom name.
        Weakening the `StateInitializer` type works around this issue but breaks
        type inference in VS Code. Using this with Mypy requires a `# type: ignore`
        comment (see example below).

    Example:
        ```python
        # register the state under the function's own name
        @state
        async def db():
            return await connect_to_db()

        # register the state under a custom name
        @state("db_connection")  # type: ignore[arg-type]
        async def db():
            return await connect_to_db()
        ```

    Args:
        init_or_name: Either the initializer function or a custom name
            under which to store the result.

    Returns:
        Either a `State` instance or a decorator that wraps a state initializer.

    """
    if callable(init_or_name):
        return State(init_or_name.__name__, init_or_name)

    def decorator(init: StateInitializer[P, R]) -> State[P, R]:
        return State(init_or_name, init)

    return decorator


class State[**P, R]:
    """Represents a named piece of application state in FastAPI.

    Stores a reference to a state initializer and the name under which
    it will be registered in `app.state`.
    """

    __slots__ = ('_init', '_name')

    def __init__(self, name: str, init: StateInitializer[P, R]) -> None:
        """Initialize a state with a name and initializer function.

        Args:
            name: The key used to store the state in the app.
            init: The function used to initialize the state value.

        """
        self._name = name
        self._init = init

    async def inject(self, app: FastAPI, *args: P.args, **kwargs: P.kwargs) -> R:
        """Inject the state into the FastAPI app.

        Raises:
            DuplicateStateNameError: If the state name already exists.

        Returns:
            The initialized state value.

        """
        name = self._name
        if hasattr(app.state, name):
            raise DuplicateStateNameError(name)

        state = self._init(*args, **kwargs)
        if inspect.isawaitable(state):
            state = await state
        setattr(app.state, name, state)

        return state

    async def extract(self, request: Request) -> R:
        """Extract the state value from a request object.

        Can be used in a FastAPI dependency definition using `Depends`.

        Example:
            ```python
            from fastapi import Depends

            @state
            async def db():
                return await connect_to_db()

            DbDependency = Annotated[DbConnection, Depends(db.extract)]
            ```

        Args:
            request: A FastAPI request instance.

        Returns:
            The stored state value.

        """
        return getattr(request.app.state, self._name)

    async def extract_ws(self, ws: WebSocket) -> R:
        """Extract the state value from a websocket object.

        Can be used in a FastAPI dependency definition using `Depends`.

        Args:
            ws: A FastAPI WebSocket instance.

        Returns:
            The stored state value.

        """
        return getattr(ws.app.state, self._name)


class DuplicateStateNameError(ValueError):
    """Raised when a state with the same name is injected more than once."""

    def __init__(self, name: str) -> None:
        """Initialize with the duplicate state name."""
        super().__init__(f'A state with name "{name}" was already injected')
