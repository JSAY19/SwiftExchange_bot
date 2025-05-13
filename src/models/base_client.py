import logging
import asyncio
import aiohttp
from fake_useragent import UserAgent
from abc import ABC
from typing import Optional, Any
from src.config.config import MAX_RETRIES_REQUEST, RETRY_DELAY


class BaseClient(ABC):
    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session

    async def make_request(
            self,
            method: str,
            endpoint: str) -> Any | None:

        url = endpoint

        for attempt in range(MAX_RETRIES_REQUEST):
            try:
                async with self.session.request(method, url, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401 or response.status == 500:
                        return response.status
                    else:
                        logging.info(
                            f'Failed to get response from server(BaseClient): {response.status}: {await response.json()}')
                        if attempt < MAX_RETRIES_REQUEST - 1:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            return None

            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES_REQUEST - 1:
                    await asyncio.sleep(RETRY_DELAY)
            except aiohttp.ClientError as e:
                logging.error(f"Request failed: {e}. Attempt {attempt + 1} of {MAX_RETRIES_REQUEST}.")
                if attempt < MAX_RETRIES_REQUEST - 1:
                    await asyncio.sleep(RETRY_DELAY)
            except Exception as general_ex:
                logging.error(
                    f"General request exception for: {general_ex}. Attempt {attempt + 1} of {MAX_RETRIES_REQUEST}.")
                if attempt < MAX_RETRIES_REQUEST - 1:
                    await asyncio.sleep(RETRY_DELAY)
