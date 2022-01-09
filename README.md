# fastapi-depends

You can use your FastAPI dependencies not only in FastAPI applications

[PYPI](https://pypi.org/project/fastapi-depends/)

## Install

pip

```bash
pip install fastapi-depends
```

poetry

```bash
poetry add fastapi-depends
```

## Usage

### Simple

Simple example for calling dependencies, without binding to `fastapi.Request` object

```python
import asyncio

from fastapi import Depends

from fastapi_depends import inject


async def str_dep():
    return "str_dep"


@inject
async def main(pos_value: str, regular_value: str, str_dep=Depends(str_dep)):
    return (pos_value, regular_value, str_dep)


if __name__ == "__main__":
    result = asyncio.run(main("pos_value", regular_value="regular_value"))
    print(f"{result=}")

```

### With your application

Example of getting a `fastapi.Request` object with one property `app`

```python
import asyncio

from fastapi import Depends, Request

from fastapi_depends import DepContainer

container = DepContainer()


async def str_dep(request: Request):
    return request.app.app_value


@container.inject
async def main(pos_value: str, regular_value: str, str_dep=Depends(str_dep)):
    return (pos_value, regular_value, str_dep)


class MyApp:
    def __init__(self, app_value):
        self.app_value = app_value


app = MyApp(app_value="app_value")
container.setup_app(app)

if __name__ == "__main__":
    result = asyncio.run(main("pos_value", regular_value="regular_value"))
    print(f"{result=}")

```

### Register the method in your application

An example similar to the previous one, but only for a method you can specify a key with which it will be written in `DepContainer.callback_map`

```python
import asyncio

from fastapi import Depends, Request

from fastapi_depends import DepContainer


async def str_dep(request: Request):
    return request.app.app_value


container = DepContainer()


@container.register("my_key")
async def main(pos_value: str, regular_value: str, str_dep=Depends(str_dep)):
    return (pos_value, regular_value, str_dep)


class MyApp:
    def __init__(self, app_value):
        self.app_value = app_value


app = MyApp(app_value="app_value")
container.setup_app(app)

if __name__ == "__main__":
    result = asyncio.run(container.callback_map["my_key"]("pos_value", regular_value="regular_value"))
    print(f"{result=}")


```
