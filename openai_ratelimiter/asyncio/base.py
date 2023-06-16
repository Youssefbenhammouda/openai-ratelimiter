import time
import types
from typing import Optional, Type

import redis.asyncio as redis
import tiktoken
from redis.asyncio.lock import Lock

# Tokenizer
CL100K_ENCODER = tiktoken.get_encoding("cl100k_base")
P50K_ENCODER = tiktoken.get_encoding("p50k_base")
period = 60


class AsyncLimiter:
    def __init__(
        self,
        model_name: str,
        max_calls: int,
        max_tokens: int,
        period: int,
        tokens: int,
        redis: "redis.Redis[bytes]",
    ):
        self.model_name = model_name
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.period = period
        self.tokens = tokens
        self.redis = redis

    async def __aenter__(self):
        lock = Lock(self.redis, f"{self.model_name}_lock", timeout=self.period)

        async with lock:
            while True:
                self.current_calls = await self.redis.incr(
                    f"{self.model_name}_api_calls", amount=1
                )
                if self.current_calls == 1:
                    await self.redis.expire(f"{self.model_name}_api_calls", self.period)
                if self.current_calls <= self.max_calls:
                    break
                else:
                    await lock.release()  # Release the lock before sleeping
                    time.sleep(self.period)  # wait for the limit to reset
                    await lock.acquire()

            while True:
                self.current_tokens = await self.redis.incrby(
                    f"{self.model_name}_api_tokens", self.tokens
                )
                if self.current_tokens == self.tokens:
                    await self.redis.expire(
                        f"{self.model_name}_api_tokens", self.period
                    )
                if self.current_tokens <= self.max_tokens:
                    break
                else:
                    await lock.release()  # Release the lock before sleeping
                    time.sleep(self.period)  # wait for the limit to reset
                    await lock.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        pass


class AsyncBaseAPILimiterRedis:
    def __init__(
        self,
        model_name: str,
        RPM: int,
        TPM: int,
        redis_host: str = "localhost",
        redis_port: int = 6379,
    ):
        """
        Initializer for the BaseAPILimiterRedis class.

        Args:
            model_name (str): The name of the model being limited.
            RPM (int): The maximum number of requests per minute allowed. You can find your rate limits in your
                       OpenAI account at https://platform.openai.com/account/rate-limits
            TPM (int): The maximum number of tokens per minute allowed. You can find your rate limits in your
                       OpenAI account at https://platform.openai.com/account/rate-limits
            redis_host (str, optional): The hostname of the Redis server. Defaults to "localhost".
            redis_port (int, optional): The port number of the Redis server. Defaults to 6379.

        Creates an instance of the BaseAPILimiterRedis with the specified parameters, and connects to a Redis server
        at the specified host and port.
        """
        self.model_name = model_name
        self.max_calls = RPM
        self.max_tokens = TPM
        self.period = period
        self.redis: "redis.Redis[bytes]" = redis.Redis(host=redis_host, port=redis_port)

    def _limit(self, tokens: int) -> AsyncLimiter:
        return AsyncLimiter(
            self.model_name,
            self.max_calls,
            self.max_tokens,
            self.period,
            tokens,
            self.redis,
        )
