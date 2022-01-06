from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


def inject(func: FuncType):
    async def inner(*args, **kwargs):
        request = FakeRequest(app={})
        values = await get_values(func, request)
        try:
            kwargs = {**kwargs, **values}
            return await func(*args, **kwargs)
        except Exception:
            raise
        finally:
            await request.scope.get("func_stack").__aexit__(None, None, None)

    return inner
