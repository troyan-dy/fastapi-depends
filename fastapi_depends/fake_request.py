from contextlib import AsyncExitStack as AsyncExitStack
from typing import Any

from fastapi import Request


class FakeRequest(Request):
    __slots__ = ["app", "scope"]

    def __init__(self, app: Any) -> None:
        self.app = app  # type: ignore[misc]
        self.scope = {"func_stack": AsyncExitStack()}
