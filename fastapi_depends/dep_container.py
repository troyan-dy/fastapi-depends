from typing import Any, Callable

from fastapi import FastAPI

from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


class DepContainer:
    def __init__(self) -> None:
        self._key_func_map: dict[str, FuncType] = {}

    @property
    def callback_map(self) -> dict[str, FuncType]:
        return self._key_func_map

    def setup_app(self, app: FastAPI) -> None:
        self.request = FakeRequest(app=app)

    def inject(self, func: FuncType) -> FuncType:
        async def inner(*args: Any, **kwargs: Any) -> Any:
            values = await get_values(func, request=self.request)
            try:
                kwargs = {**kwargs, **values}
                return await func(*args, **kwargs)
            except Exception:
                raise
            finally:
                await self.request.scope["func_stack"].__aexit__(None, None, None)

        return inner

    def register(self, key: str) -> Callable[[FuncType], FuncType]:
        def inject(func: FuncType) -> FuncType:
            async def inner(*args: Any, **kwargs: Any) -> Any:
                values = await get_values(func, request=self.request)
                try:
                    kwargs = {**kwargs, **values}
                    return await func(*args, **kwargs)
                except Exception:
                    raise
                finally:
                    await self.request.scope["func_stack"].__aexit__(None, None, None)

            self._key_func_map[key] = inner
            return inner

        return inject
