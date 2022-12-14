import aiohttp
import asyncio
from typing import Dict
import utype


@utype.parse
async def fetch(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print('URL:', url)
            return await response.text()


@utype.parse
async def fetch_urls(*urls: str) -> Dict[str, dict]:
    result = {}
    tasks = []

    async def task(loc):
        result[loc] = await fetch(loc)

    for url in urls:
        tasks.append(asyncio.create_task(task(url)))

    await asyncio.gather(*tasks)
    return result

# def awaitable_fetch_urls(urls: List[str]) -> Awaitable[Dict[str, dict]]:
#     return fetch_urls(urls)


async def main():
    urls = [
        b'https://httpbin.org/get?k1=v1',
        b'https://httpbin.org/get?k1=v1&k2=v2',
        b'https://httpbin.org/get',
    ]
    result_map = await fetch_urls(*urls)
    for url, res in result_map.items():
        print(url, ': query =', res)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    # asyncio.run(main())
