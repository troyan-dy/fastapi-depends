from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


class DepContainer:
    def __init__(self, request: FakeRequest) -> None:
        self.request = request

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

            setattr(self.request.app, key, inner)
            return inner

        return inject
