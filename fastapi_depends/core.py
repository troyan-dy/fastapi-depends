from typing import Any, Callable, Optional, cast

from fastapi import Request, params
from fastapi.dependencies.utils import (
    Dependant,
    get_param_sub_dependant,
    get_typed_signature,
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
    run_in_threadpool,
    solve_generator,
)

from fastapi_depends.fake_request import FakeRequest

FuncType = Callable[..., Any]


def get_dependant(
    *,
    path: str,
    call: Callable[..., Any],
    name: Optional[str] = None,
    security_scopes: Optional[list[str]] = None,
    use_cache: bool = True,
) -> Dependant:
    endpoint_signature = get_typed_signature(call)
    signature_params = endpoint_signature.parameters
    dependant = Dependant(call=call, name=name, path=path, use_cache=use_cache)
    for _, param in signature_params.items():
        if isinstance(param.default, params.Depends):
            sub_dependant = get_param_sub_dependant(param=param, path=path, security_scopes=security_scopes)
            dependant.dependencies.append(sub_dependant)
            continue
    return dependant


async def solve_dependencies(
    *,
    request: FakeRequest,
    dependant: Dependant,
    dependency_overrides_provider=None,
    dependency_cache: dict[str, Any] = None,
) -> tuple[dict[str, Any]]:
    values: dict[str, Any] = {}

    dependency_cache = {}
    sub_dependant: Dependant
    for sub_dependant in dependant.dependencies:
        sub_dependant.call = cast(Callable[..., Any], sub_dependant.call)
        sub_dependant.cache_key = cast(tuple[Callable[..., Any], tuple[str]], sub_dependant.cache_key)
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
                security_scopes=sub_dependant.security_scopes,
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

        if sub_dependant.use_cache and sub_dependant.cache_key in dependency_cache:
            solved = dependency_cache[sub_dependant.cache_key]
        elif is_gen_callable(call) or is_async_gen_callable(call):
            stack = request.scope.get("func_stack")
            solved = await solve_generator(call=call, stack=stack, sub_values=sub_values)
        elif is_coroutine_callable(call):
            solved = await call(**sub_values)
        else:
            solved = await run_in_threadpool(call, **sub_values)
        if sub_dependant.name is not None:
            values[sub_dependant.name] = solved
        if sub_dependant.cache_key not in dependency_cache:
            dependency_cache[sub_dependant.cache_key] = solved
    if dependant.request_param_name and isinstance(request, Request):
        values[dependant.request_param_name] = request
    return values, None, dependency_cache


async def get_values(func: FuncType, request: FakeRequest):
    values, _, _ = await solve_dependencies(request=request, dependant=get_dependant(call=func, path="my_topic"))
    return values
