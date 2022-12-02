import utype
from typing import AsyncGenerator
import asyncio


@utype.parse
async def waiter(rounds: int = utype.Field(gt=0)) -> AsyncGenerator[int, float]:
    assert isinstance(rounds, int)
    i = rounds
    while i:
        wait = yield str(i)
        if wait:
            assert isinstance(wait, float)
            await asyncio.sleep(wait)
        i -= 1


async def test():
    wait_gen = waiter('-1')
    async for index in wait_gen:
        assert isinstance(index, int)
        try:
            await wait_gen.asend(b'0.5')
            # wait for 0.5 seconds
        except StopAsyncIteration:
            return

if __name__ == '__main__':
    asyncio.run(test())
