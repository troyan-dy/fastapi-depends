from contextlib import AsyncExitStack as AsyncExitStack

from fastapi import Request


class FakeRequest(Request):
    __slots__ = ["app", "scope"]

    def __init__(self, app):
        self.app = app
        self.scope = {"func_stack": AsyncExitStack()}
