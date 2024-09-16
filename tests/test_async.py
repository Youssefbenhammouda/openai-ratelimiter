import asyncio

import pytest
import redis.asyncio as redis

from openai_ratelimiter.asyncio import AsyncChatCompletionLimiter, AsyncDalleLimiter

model_name = "gpt-3.5-turbo-16k"
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of Morocco."},
]


@pytest.mark.asyncio()
async def test_async_redis_TPM():
    redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )
    max_tokens = 200
    achatlimiter = AsyncChatCompletionLimiter(
        model_name=model_name,
        RPM=3_000,  # we will ignore this by setting a high value, we will make another test to test this.
        TPM=1_125,  # 1_125 = 225 * 5
        redis_instance=redis_instance,
    )
    await achatlimiter.check_redis()
    await achatlimiter.clear_locks()
    achatlimiter.period = 5

    async def make_request():
        await achatlimiter.limit(messages=messages, max_tokens=max_tokens).__aenter__()

    for _ in range(5):
        try:
            assert (
                await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens)
            ) == False
            await asyncio.wait_for(make_request(), timeout=2)
        except (asyncio.TimeoutError, AssertionError):
            pytest.fail("The request should have been completed.")
    if not await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens):
        pytest.fail("The request should have timed out.")
    await asyncio.sleep(7)
    if await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens):
        pytest.fail("The lock should have expired.")


@pytest.mark.asyncio()
async def test_async_memory_TPM():

    max_tokens = 200
    achatlimiter = AsyncChatCompletionLimiter(
        model_name=model_name,
        RPM=3_000,  # we will ignore this by setting a high value, we will make another test to test this.
        TPM=1_125,  # 1_125 = 225 * 5
    )
    await achatlimiter.check_redis()
    await achatlimiter.clear_locks()
    achatlimiter.period = 5

    async def make_request():
        await achatlimiter.limit(messages=messages, max_tokens=max_tokens).__aenter__()

    for _ in range(5):
        try:
            assert (
                await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens)
            ) == False
            await asyncio.wait_for(make_request(), timeout=2)
        except (asyncio.TimeoutError, AssertionError):
            pytest.fail("The request should have been completed.")
    if not await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens):
        pytest.fail("The request should have timed out.")
    await asyncio.sleep(7)
    if await achatlimiter.is_locked(messages=messages, max_tokens=max_tokens):
        pytest.fail("The lock should have expired.")


@pytest.mark.asyncio()
async def test_async_dalle():

    achatlimiter = AsyncDalleLimiter(
        model_name="dall-e-2",
        IPM=5,
    )
    await achatlimiter.check_redis()
    await achatlimiter.clear_locks()
    achatlimiter.period = 5

    async def make_request():
        await achatlimiter.limit().__aenter__()

    for _ in range(5):
        try:
            assert (await achatlimiter.is_locked()) == False
            await asyncio.wait_for(make_request(), timeout=2)
        except (asyncio.TimeoutError, AssertionError):
            pytest.fail("The request should have been completed.")
    if not await achatlimiter.is_locked():
        pytest.fail("The request should have timed out.")
    await asyncio.sleep(7)
    if await achatlimiter.is_locked():
        pytest.fail("The lock should have expired.")
