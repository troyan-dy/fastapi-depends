import asyncio

from fastapi import Depends as _
from fastapi import Request

from fastapi_depends import DepContainer, FakeRequest


class MyApp:
    def __init__(self, app_value):
        self.app_value = app_value


my_app = MyApp(app_value="app_value")

app = DepContainer(request=FakeRequest(app=my_app))


async def str_dep(request: Request):
    return request.app.app_value


@app.inject
async def main(pos_value: str, regular_value: str, str_dep=_(str_dep)):
    return (pos_value, regular_value, str_dep)


if __name__ == "__main__":
    result = asyncio.run(main("pos_value", regular_value="regular_value"))
    print(f"{result=}")
