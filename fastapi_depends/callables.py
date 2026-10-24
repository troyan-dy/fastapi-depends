import inspect
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import Any, Callable

from fastapi.concurrency import contextmanager_in_threadpool, run_in_threadpool


def _get_callable(call: Callable[..., Any]) -> Any:
    if inspect.isroutine(call):
        return call
    return getattr(call, "__call__", None)


def is_gen_callable(call: Callable[..., Any]) -> bool:
    return inspect.isgeneratorfunction(_get_callable(call))


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    return inspect.isasyncgenfunction(_get_callable(call))


def is_coroutine_callable(call: Callable[..., Any]) -> bool:
    return inspect.iscoroutinefunction(_get_callable(call))


async def solve_generator(
    *,
    call: Callable[..., Any],
    stack: AsyncExitStack,
    sub_values: dict[str, Any],
) -> Any:
    if is_async_gen_callable(call):
        cm = asynccontextmanager(call)(**sub_values)
    else:
        cm = contextmanager_in_threadpool(contextmanager(call)(**sub_values))
    return await stack.enter_async_context(cm)


async def call_dependency(
    *,
    call: Callable[..., Any],
    stack: AsyncExitStack,
    sub_values: dict[str, Any],
) -> Any:
    if is_gen_callable(call) or is_async_gen_callable(call):
        return await solve_generator(call=call, stack=stack, sub_values=sub_values)
    if is_coroutine_callable(call):
        return await call(**sub_values)
    return await run_in_threadpool(call, **sub_values)
