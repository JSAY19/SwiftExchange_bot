import aiohttp
import asyncio

from src.models.base_client import BaseClient


class CoinGeckoClient(BaseClient):
    def __init__(self, session: aiohttp.ClientSession):
        self.api_url = 'https://api.coingecko.com/api/v3/simple/price'

        super().__init__(session=session)

    async def get_rate(self):
        data_usdt_thb = await self.make_request(method='GET', endpoint=f'{self.api_url}?ids=tether&vs_currencies=thb')
        usdt_thb = float(data_usdt_thb['tether']['thb'])
        data_usdt_rub = await self.make_request(method='GET', endpoint=f'{self.api_url}?ids=tether&vs_currencies=rub')
        usdt_rub = float(data_usdt_rub['tether']['rub'])
        if usdt_thb and usdt_rub:
            rub_thb = usdt_thb / usdt_rub
            rates = {
                'USDT/THB': usdt_thb,
                'RUB/THB': rub_thb,
            }
            return rates
        else:
            return None


async def main():
    async with aiohttp.ClientSession() as session:
        gecko = CoinGeckoClient(session=session)
        response = await gecko.get_rate()
        print(response)


if __name__ == '__main__':
    asyncio.run(main())
