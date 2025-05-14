import aiohttp
import asyncio

from src.models.base_client import BaseClient


class CoinGeckoClient(BaseClient):
    def __init__(self, session: aiohttp.ClientSession):
        self.api_url = "https://open.er-api.com/v6/latest/"

        super().__init__(session=session)

    async def get_rate(self):
        data_usdt_thb = await self.make_request(method='GET', endpoint=f"{self.api_url}USDT")
        data_rub_thb = await self.make_request(method='GET', endpoint=f"{self.api_url}RUB")

        if data_rub_thb.get("result") == "success" and data_usdt_thb.get("result") == "success":
            rub_thb = float(data_rub_thb["rates"]["THB"])
            usdt_thb = float(data_usdt_thb["rates"]["THB"])

            if rub_thb != 0 and usdt_thb != 0:
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
