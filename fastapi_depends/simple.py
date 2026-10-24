from typing import Any

from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


def inject(func: FuncType) -> FuncType:
    async def inner(*args: Any, **kwargs: Any) -> Any:
        request = FakeRequest(app={})
        values = await get_values(func, request)
        try:
            kwargs = {**kwargs, **values}
            return await func(*args, **kwargs)
        except Exception:
            raise
        finally:
            await request.scope["func_stack"].__aexit__(None, None, None)

    return inner
