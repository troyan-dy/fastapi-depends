from typing import Any, Callable, Optional, cast

from fastapi import Request, params
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant as get_sub_dependant
from fastapi.dependencies.utils import get_typed_signature

from fastapi_depends.callables import call_dependency
from fastapi_depends.fake_request import FakeRequest

FuncType = Callable[..., Any]
ScopesKey = tuple[str, ...]
CacheKey = tuple[FuncType, ScopesKey]
DepValues = dict[str, Any]
DepCache = dict[CacheKey, Any]
SolvedDependencies = tuple[DepValues, None, DepCache]


def get_dependant(
    *,
    path: str,
    call: FuncType,
    name: Optional[str] = None,
    use_cache: bool = True,
) -> Dependant:
    dependant = Dependant(call=call, name=name, path=path, use_cache=use_cache)
    for param_name, sig_param in get_typed_signature(call).parameters.items():
        if isinstance(sig_param.default, params.Depends):
            dependant.dependencies.append(_get_param_sub_dependant(param_name, sig_param.default, sig_param, path))
    return dependant


def _get_param_sub_dependant(param_name: str, depends: params.Depends, sig_param: Any, path: str) -> Dependant:
    return get_sub_dependant(
        path=path,
        call=depends.dependency or sig_param.annotation,
        name=param_name,
        use_cache=depends.use_cache,
    )


def _resolve_override(sub_dependant: Dependant, overrides_provider: Any) -> tuple[FuncType, Dependant]:
    call = cast(FuncType, sub_dependant.call)
    if not (overrides_provider and overrides_provider.dependency_overrides):
        return call, sub_dependant
    overrides = getattr(overrides_provider, "dependency_overrides", {})
    call = overrides.get(call, call)
    path = cast(str, sub_dependant.path)
    return call, get_dependant(path=path, call=call, name=sub_dependant.name)


async def solve_dependencies(
    *,
    request: FakeRequest,
    dependant: Dependant,
    dependency_overrides_provider: Any = None,
    dependency_cache: Optional[DepCache] = None,
) -> SolvedDependencies:
    dep_values: DepValues = {}

    dependency_cache = {}
    for sub_dependant in dependant.dependencies:
        # dependencies are solved one by one: order matters for the cache and the exit stack
        solved = await _solve_sub_dependant(  # noqa: WPS476
            request=request,
            sub_dependant=sub_dependant,
            overrides_provider=dependency_overrides_provider,
            dependency_cache=dependency_cache,
        )
        if sub_dependant.name is not None:
            dep_values[sub_dependant.name] = solved
    if dependant.request_param_name and isinstance(request, Request):
        dep_values[dependant.request_param_name] = request
    return dep_values, None, dependency_cache


async def _solve_sub_dependant(
    *,
    request: FakeRequest,
    sub_dependant: Dependant,
    overrides_provider: Any,
    dependency_cache: DepCache,
) -> Any:
    call, use_sub_dependant = _resolve_override(sub_dependant, overrides_provider)
    sub_values, _, sub_dependency_cache = await solve_dependencies(
        request=request,
        dependant=use_sub_dependant,
        dependency_overrides_provider=overrides_provider,
        dependency_cache=dependency_cache,
    )
    dependency_cache.update(sub_dependency_cache)
    return await _call_or_get_cached(
        call=call,
        sub_dependant=sub_dependant,
        request=request,
        sub_values=sub_values,
        dependency_cache=dependency_cache,
    )


async def _call_or_get_cached(
    *,
    call: FuncType,
    sub_dependant: Dependant,
    request: FakeRequest,
    sub_values: DepValues,
    dependency_cache: DepCache,
) -> Any:
    # security scopes are not part of the cache key, as in the previous implementation
    cache_key: CacheKey = (cast(FuncType, sub_dependant.call), ())
    if sub_dependant.use_cache and cache_key in dependency_cache:
        return dependency_cache[cache_key]
    solved = await call_dependency(call=call, stack=request.scope["func_stack"], sub_values=sub_values)
    dependency_cache.setdefault(cache_key, solved)
    return solved


async def get_values(func: FuncType, request: FakeRequest) -> DepValues:
    dependant = get_dependant(call=func, path="my_topic")
    dep_values, _, _ = await solve_dependencies(request=request, dependant=dependant)
    return dep_values
