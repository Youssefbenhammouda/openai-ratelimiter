import asyncio
import types
from typing import Dict, Optional, Type, Union

import redis.asyncio as redis
import tiktoken
from redis.asyncio.lock import Lock

# Tokenizer


period = 60


class AsyncRedisLimiter:
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
                    await asyncio.sleep(self.period)  # wait for the limit to reset
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
                    await asyncio.sleep(self.period)  # wait for the limit to reset
                    await lock.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        pass

    async def clear_locks(self) -> bool:
        """
        This method will clear all locks associated with the model.
        returns True if the locks were cleared successfully, otherwise returns False.
        """
        keys_to_delete = await self.redis.keys(f"{self.model_name}_*")
        if keys_to_delete:
            await self.redis.delete(*keys_to_delete)
            return True
        return False

    async def is_locked(self, tokens: int) -> bool:
        """
        This method will check if there are any locks associated with the model.

        Args:
            tokens (int): The number of tokens to be used for the check.

        Returns:
            bool: True if the lock is held, False otherwise.
        """
        api_calls_key_exists = await self.redis.exists(f"{self.model_name}_api_calls")
        api_tokens_key_exists = await self.redis.exists(f"{self.model_name}_api_tokens")

        # If both keys exist and their values exceed the allowed limits, return True
        if api_calls_key_exists and api_tokens_key_exists:
            current_calls = int((await self.redis.get(f"{self.model_name}_api_calls")))  # type: ignore
            current_tokens = int((await self.redis.get(f"{self.model_name}_api_tokens")))  # type: ignore
            if (
                current_calls >= self.max_calls
                or current_tokens + tokens > self.max_tokens
            ):
                return True

        return False

    async def check_redis(
        self,
    ):

        return await self.redis.ping()


class AsyncMemoryLimiter:
    memory_store: Dict[str, int] = {}
    locks: Dict[str, asyncio.Lock] = {}

    def __init__(
        self,
        model_name: str,
        max_calls: int,
        max_tokens: int,
        period: int,
        tokens: int,
    ):
        self.model_name = model_name
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.period = period
        self.tokens = tokens

    async def __aenter__(self):
        lock = self.locks.setdefault(self.model_name, asyncio.Lock())

        async with lock:
            while True:
                self.current_calls = (
                    self.memory_store.get(f"{self.model_name}_api_calls", 0) + 1
                )
                self.memory_store[f"{self.model_name}_api_calls"] = self.current_calls
                if self.current_calls == 1:
                    asyncio.create_task(
                        self._expire_key(f"{self.model_name}_api_calls", self.period)
                    )
                if self.current_calls <= self.max_calls:
                    break
                else:
                    lock.release()  # Release the lock before sleeping
                    await asyncio.sleep(self.period)  # wait for the limit to reset
                    await lock.acquire()

            while True:
                self.current_tokens = (
                    self.memory_store.get(f"{self.model_name}_api_tokens", 0)
                    + self.tokens
                )
                self.memory_store[f"{self.model_name}_api_tokens"] = self.current_tokens
                if self.current_tokens == self.tokens:
                    asyncio.create_task(
                        self._expire_key(f"{self.model_name}_api_tokens", self.period)
                    )
                if self.current_tokens <= self.max_tokens:
                    break
                else:
                    lock.release()  # Release the lock before sleeping
                    await asyncio.sleep(self.period)  # wait for the limit to reset
                    await lock.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        pass

    async def clear_locks(self) -> bool:
        """
        This method will clear all locks associated with the model.
        returns True if the locks were cleared successfully, otherwise returns False.
        """
        keys_to_delete = [
            key for key in self.memory_store if key.startswith(f"{self.model_name}_")
        ]
        for key in keys_to_delete:
            del self.memory_store[key]
        return bool(keys_to_delete)

    # this function does'nt need self

    async def is_locked(self, tokens: int) -> bool:
        """
        This method will check if there are any locks associated with the model.

        Args:
            tokens (int): The number of tokens to be used for the check.

        Returns:
            bool: True if the lock is held, False otherwise.
        """
        current_calls = self.memory_store.get(f"{self.model_name}_api_calls", 0)
        current_tokens = self.memory_store.get(f"{self.model_name}_api_tokens", 0)

        if current_calls >= self.max_calls or current_tokens + tokens > self.max_tokens:
            return True

        return False

    async def _expire_key(self, key: str, period: int):
        """
        This method will expire a key from the memory store after a given period.

        Args:
            key (str): The key to be expired.
            period (int): The expiration period in seconds.
        """
        await asyncio.sleep(period)
        if key in self.memory_store:
            del self.memory_store[key]


class AsyncBaseAPILimiterRedis:
    def __init__(
        self,
        model_name: str,
        RPM: int,
        TPM: int,
        redis_instance: "redis.Redis[bytes] | None" = None,
    ):
        """
        Initializer for the BaseAPILimiterRedis class.

        Args:
            model_name (str): The name of the model being limited.
            RPM (int): The maximum number of requests per minute allowed. You can find your rate limits in your
                       OpenAI account at https://platform.openai.com/account/rate-limits
            TPM (int): The maximum number of tokens per minute allowed. You can find your rate limits in your
                       OpenAI account at https://platform.openai.com/account/rate-limits
            redis_instance (redis.Redis[bytes] | None): Optional: The redis instance. If not specified it will use in-memory caching.

        Creates an instance of the BaseAPILimiterRedis with the specified parameters, and connects to a Redis server
        at the specified host and port.
        """
        self.model_name = model_name
        self.max_calls = RPM
        self.max_tokens = TPM
        self.period = period
        self.redis = redis_instance
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoder = None

    def _limit(self, tokens: int) -> Union[AsyncRedisLimiter, AsyncMemoryLimiter]:

        if self.redis:
            instance: Union[AsyncRedisLimiter, AsyncMemoryLimiter] = AsyncRedisLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                tokens,
                self.redis,
            )
        else:
            instance = AsyncMemoryLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                tokens,
            )
        return instance

    async def _is_locked(self, tokens: int) -> bool:
        if self.redis:
            instance: Union[AsyncRedisLimiter, AsyncMemoryLimiter] = AsyncRedisLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                tokens,
                self.redis,
            )
        else:
            instance = AsyncMemoryLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                tokens,
            )
        return await instance.is_locked(tokens)

    async def check_redis(self):
        if self.redis:
            return await self.redis.ping()
        return False

    async def clear_locks(self) -> bool:
        if self.redis:
            instance: Union[AsyncRedisLimiter, AsyncMemoryLimiter] = AsyncRedisLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                0,
                self.redis,
            )
        else:
            instance = AsyncMemoryLimiter(
                self.model_name,
                self.max_calls,
                self.max_tokens,
                self.period,
                0,
            )
        return await instance.clear_locks()
