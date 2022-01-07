import asyncio

from fastapi import Depends, Request

from fastapi_depends import DepContainer


async def str_dep(request: Request):
    return request.app.app_value


container = DepContainer()
import pydantic


class MyType(pydantic.BaseModel):
    key: str


@container.register("my_key")
async def main(pos_value: MyType, regular_value: str, str_dep=Depends(str_dep)):
    return (pos_value, regular_value, str_dep)


class MyApp:
    def __init__(self, app_value):
        self.app_value = app_value


app = MyApp(app_value="app_value")
container.setup_app(app)

if __name__ == "__main__":
    result = asyncio.run(container.callback_map["my_key"]("pos_value", regular_value="regular_value"))
    print(f"{result=}")
