import asyncio

from examples.test_dep_container import main as custom_request_call
from examples.test_dep_key import container as container
from examples.test_simple import main as simple_call

POS_VALUE = "pos_value"
KEY_VALUE = "key_value"


if __name__ == "__main__":
    simple_call_result = asyncio.run(simple_call(POS_VALUE, regular_value=KEY_VALUE))
    custom_request_call_result = asyncio.run(custom_request_call(POS_VALUE, regular_value=KEY_VALUE))
    container_with_key_func_map_result = asyncio.run(
        container.key_func_map["my_key"](POS_VALUE, regular_value=KEY_VALUE)
    )

    print(f"{simple_call_result=}")
    print(f"{custom_request_call_result=}")
    print(f"{container_with_key_func_map_result=}")
