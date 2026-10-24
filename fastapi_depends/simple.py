from typing import Any

from fastapi_depends.core import FuncType, get_values
from fastapi_depends.fake_request import FakeRequest


def inject(func: FuncType) -> FuncType:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = FakeRequest(app={})
        dep_values = await get_values(func, request)
        kwargs = {**kwargs, **dep_values}
        try:
            return await func(*args, **kwargs)
        except Exception:
            raise
        finally:
            await request.scope["func_stack"].__aexit__(None, None, None)

    return wrapper
