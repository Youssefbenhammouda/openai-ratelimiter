from typing import Any, Dict, List, Union

from redis.asyncio import Redis
from tiktoken.core import Encoding

from .base import AsyncBaseAPILimiterRedis, AsyncMemoryLimiter, AsyncRedisLimiter


def num_tokens_consumed_by_chat_request(
    messages: List[Dict[str, str]], encoder: Encoding, max_tokens: int = 15, n: int = 1
):
    num_tokens = n * max_tokens
    for message in messages:
        num_tokens += (
            4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        )
        for key, value in message.items():
            num_tokens += len(encoder.encode(value))

            if key == "name":  # If there's a name, the role is omitted
                num_tokens -= 1

    num_tokens += 2  # Every reply is primed with <im_start>assistant

    return num_tokens


def num_tokens_consumed_by_completion_request(
    prompt: Union[str, list[str], Any],
    encoder: Encoding,
    max_tokens: int = 15,
    n: int = 1,
):
    num_tokens = n * max_tokens
    if isinstance(prompt, str):  # Single prompt
        num_tokens += len(encoder.encode(prompt))
    elif isinstance(prompt, list):  # Multiple prompts
        num_tokens *= len(prompt)
        num_tokens += sum([len([encoder.encode(p) for p in prompt])])
    else:
        raise TypeError(
            "Either a string or list of strings expected for 'prompt' field in completion request."
        )

    return num_tokens


class AsyncChatCompletionLimiter(AsyncBaseAPILimiterRedis):
    def limit(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> AsyncRedisLimiter | AsyncMemoryLimiter:
        if not self.encoder:
            raise ValueError("The encoder is not set.")
        tokens = num_tokens_consumed_by_chat_request(messages, self.encoder, max_tokens)
        return self._limit(tokens)

    async def is_locked(self, messages: List[Dict[str, str]], max_tokens: int) -> bool:
        if not self.encoder:
            raise ValueError("The encoder is not set.")
        tokens = num_tokens_consumed_by_chat_request(messages, self.encoder, max_tokens)
        return await self._is_locked(tokens)


class AsyncTextCompletionLimiter(AsyncBaseAPILimiterRedis):
    def limit(
        self, prompt: str, max_tokens: int
    ) -> AsyncRedisLimiter | AsyncMemoryLimiter:
        if not self.encoder:
            raise ValueError("The encoder is not set.")
        tokens = num_tokens_consumed_by_completion_request(
            prompt, self.encoder, max_tokens
        )
        return self._limit(tokens)

    async def is_locked(self, prompt: str, max_tokens: int) -> bool:
        if not self.encoder:
            raise ValueError("The encoder is not set.")
        tokens = num_tokens_consumed_by_completion_request(
            prompt, self.encoder, max_tokens
        )
        return await self._is_locked(tokens)


class AsyncDalleLimiter(AsyncBaseAPILimiterRedis):
    def __init__(
        self, model_name: str, IPM: int, redis_instance: "Redis[bytes] | None" = None
    ):
        """
        Initializes an instance of the class.

        Args:
            model_name (str): The name of the model (dall-e-2 or dall-e-3).
            IPM (int): The maximum number of images per minute.
            Optional: redis_instance (Redis[bytes]): An instance of the Redis client. If not specified it will use in-memory caching.


        """
        """"""
        super().__init__(model_name, IPM, 1, redis_instance)

    def limit(self):
        """
        Limits the rate of API requests.
        Returns:
            Limiter: Limiter class to be used in the context manager.
        """

        return self._limit(0)

    async def is_locked(self) -> bool:
        """Returns True if the request would be locked, False otherwise."""
        return await self._is_locked(0)
