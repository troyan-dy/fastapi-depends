import inspect
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import Any, Callable, Optional, cast

from fastapi import Request, params
from fastapi.concurrency import contextmanager_in_threadpool, run_in_threadpool
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant as get_sub_dependant
from fastapi.dependencies.utils import get_typed_signature

from fastapi_depends.fake_request import FakeRequest

FuncType = Callable[..., Any]
CacheKey = tuple[Callable[..., Any], tuple[str, ...]]


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


def get_cache_key(dependant: Dependant) -> CacheKey:
    # security scopes are not part of the key, as in the previous implementation
    return cast(Callable[..., Any], dependant.call), ()


async def solve_generator(*, call: Callable[..., Any], stack: AsyncExitStack, sub_values: dict[str, Any]) -> Any:
    if is_async_gen_callable(call):
        cm = asynccontextmanager(call)(**sub_values)
    else:
        cm = contextmanager_in_threadpool(contextmanager(call)(**sub_values))
    return await stack.enter_async_context(cm)


def get_dependant(
    *,
    path: str,
    call: Callable[..., Any],
    name: Optional[str] = None,
    own_oauth_scopes: Optional[list[str]] = None,
    parent_oauth_scopes: Optional[list[str]] = None,
    use_cache: bool = True,
) -> Dependant:
    endpoint_signature = get_typed_signature(call)
    signature_params = endpoint_signature.parameters
    dependant = Dependant(
        call=call,
        name=name,
        path=path,
        use_cache=use_cache,
        own_oauth_scopes=own_oauth_scopes,
        parent_oauth_scopes=parent_oauth_scopes,
    )
    current_scopes = (parent_oauth_scopes or []) + (own_oauth_scopes or [])
    for param_name, param in signature_params.items():
        if isinstance(param.default, params.Depends):
            depends = param.default
            sub_own_oauth_scopes = list(depends.scopes or []) if isinstance(depends, params.Security) else []
            sub_dependant = get_sub_dependant(
                path=path,
                call=depends.dependency or param.annotation,
                name=param_name,
                own_oauth_scopes=sub_own_oauth_scopes,
                parent_oauth_scopes=current_scopes,
                use_cache=depends.use_cache,
            )
            dependant.dependencies.append(sub_dependant)
            continue
    return dependant


async def solve_dependencies(
    *,
    request: FakeRequest,
    dependant: Dependant,
    dependency_overrides_provider: Any = None,
    dependency_cache: Optional[dict[CacheKey, Any]] = None,
) -> tuple[dict[str, Any], None, dict[CacheKey, Any]]:
    values: dict[str, Any] = {}

    dependency_cache = {}
    sub_dependant: Dependant
    for sub_dependant in dependant.dependencies:
        sub_dependant.call = cast(Callable[..., Any], sub_dependant.call)
        cache_key = get_cache_key(sub_dependant)
        call = sub_dependant.call
        use_sub_dependant = sub_dependant
        if dependency_overrides_provider and dependency_overrides_provider.dependency_overrides:
            original_call = sub_dependant.call
            call = getattr(dependency_overrides_provider, "dependency_overrides", {}).get(original_call, original_call)
            use_path: str = sub_dependant.path  # type: ignore
            use_sub_dependant = get_dependant(
                path=use_path,
                call=call,
                name=sub_dependant.name,
                own_oauth_scopes=sub_dependant.own_oauth_scopes,
                parent_oauth_scopes=sub_dependant.parent_oauth_scopes,
            )

        solved_result = await solve_dependencies(
            request=request,
            dependant=use_sub_dependant,
            dependency_overrides_provider=dependency_overrides_provider,
            dependency_cache=dependency_cache,
        )
        (
            sub_values,
            _,
            sub_dependency_cache,
        ) = solved_result
        dependency_cache.update(sub_dependency_cache)

        if sub_dependant.use_cache and cache_key in dependency_cache:
            solved = dependency_cache[cache_key]
        elif is_gen_callable(call) or is_async_gen_callable(call):
            stack = cast(AsyncExitStack, request.scope.get("func_stack"))
            solved = await solve_generator(call=call, stack=stack, sub_values=sub_values)
        elif is_coroutine_callable(call):
            solved = await call(**sub_values)
        else:
            solved = await run_in_threadpool(call, **sub_values)
        if sub_dependant.name is not None:
            values[sub_dependant.name] = solved
        if cache_key not in dependency_cache:
            dependency_cache[cache_key] = solved
    if dependant.request_param_name and isinstance(request, Request):
        values[dependant.request_param_name] = request
    return values, None, dependency_cache


async def get_values(func: FuncType, request: FakeRequest) -> dict[str, Any]:
    values, _, _ = await solve_dependencies(request=request, dependant=get_dependant(call=func, path="my_topic"))
    return values
