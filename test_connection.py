import aiohttp
import asyncio

async def test():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.telegram.org') as resp:
                print(f'Status: {resp.status}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(test())
