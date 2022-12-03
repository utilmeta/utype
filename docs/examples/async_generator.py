import utype
import asyncio
from typing import AsyncGenerator


@utype.parse
async def waiter(rounds: int = utype.Field(gt=0)) -> AsyncGenerator[int, float]:
    assert isinstance(rounds, int)
    i = rounds
    while i:
        wait = yield str(i)
        if wait:
            assert isinstance(wait, float)
            print(f'sleep for: {wait} seconds')
            await asyncio.sleep(wait)
        i -= 1


async def wait():
    wait_gen = waiter("2")
    async for index in wait_gen:
        assert isinstance(index, int)
        try:
            await wait_gen.asend(b"0.5")
            # wait for 0.5 seconds
        except StopAsyncIteration:
            return


if __name__ == "__main__":
    asyncio.run(wait())
