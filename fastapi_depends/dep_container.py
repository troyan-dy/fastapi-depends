from fastapi import FastAPI

from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


class DepContainer:
    def __init__(self) -> None:
        self.key_func_map = {}

    @property
    def callback_map(self):
        return self.key_func_map

    def setup_app(self, app: FastAPI):
        self.request = FakeRequest(app=app)

    def inject(self, func: FuncType):
        async def inner(*args, **kwargs):
            values = await get_values(func, request=self.request)
            try:
                kwargs = {**kwargs, **values}
                return await func(*args, **kwargs)
            except Exception:
                raise
            finally:
                await self.request.scope.get("func_stack").__aexit__(None, None, None)

        return inner

    def register(self, key: str):
        def inject(func: FuncType):
            async def inner(*args, **kwargs):
                values = await get_values(func, request=self.request)
                try:
                    kwargs = {**kwargs, **values}
                    return await func(*args, **kwargs)
                except Exception:
                    raise
                finally:
                    await self.request.scope.get("func_stack").__aexit__(None, None, None)

            self.key_func_map[key] = inner
            return inner

        return inject
