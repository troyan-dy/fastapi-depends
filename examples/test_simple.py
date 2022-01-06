import asyncio

from fastapi import Depends as _

from fastapi_depends import inject


async def str_dep():
    return "str_dep"


@inject
async def main(pos_value: str, regular_value: str, str_dep=_(str_dep)):
    return (pos_value, regular_value, str_dep)


if __name__ == "__main__":
    result = asyncio.run(main("pos_value", regular_value="regular_value"))
    print(f"{result=}")
