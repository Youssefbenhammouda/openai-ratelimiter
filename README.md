
# openai-ratelimiter

openai-ratelimiter is a simple and efficient rate limiter for the OpenAI API. It is designed to help prevent the API rate limit from being reached when using the OpenAI library. Currently, it  Redis as the caching service + in-memory caching only for async version.

> **Note**: This package has been tested lastly with Python 3.12.1

## Installation

To install the [openai-ratelimiter](https://pypi.org/project/openai-ratelimiter/) library, use pip:

```shell
pip install openai-ratelimiter
```

## Redis Setup

This library uses Redis for caching. If you don't have a Redis server setup, you can pull the Redis Docker image and run a container as follows:

```shell
# Pull the Redis image
docker pull redis

# Run the Redis container
docker run --name some-redis -p 6379:6379 -d redis
```

This will set up a Redis server accessible at `localhost` on port `6379`.

## Usage

The library provides two classes, `ChatCompletionLimiter` and `TextCompletionLimiter`, for limiting the rate of API calls.

### ChatCompletionLimiter

```python
from openai_ratelimiter import ChatCompletionLimiter
import openai
import redis

redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )

openai.api_key = "{your API key}"
model_name = "gpt-3.5-turbo-16k"
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of Morocco."},
]
max_tokens = 200
chatlimiter = ChatCompletionLimiter(
    model_name=model_name,
    RPM=3_000,
    TPM=250_000,
    redis_instance = redis_instance,
    
)
with chatlimiter.limit(messages=messages, max_tokens=max_tokens):
    response = openai.ChatCompletion.create(
        model=model_name, messages=messages, max_tokens=max_tokens
    )
    ...
```

### TextCompletionLimiter

```python
from openai_ratelimiter import TextCompletionLimiter
import openai
import redis

redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )

openai.api_key = "{your API key}"
model_name = "text-davinci-003"
prompt = "What is the capital of Morocco."
max_tokens = 200
textlimiter = TextCompletionLimiter(
    model_name=model_name,
    RPM=3_000,
    TPM=250_000,
    redis_instance = redis_instance,
)
with textlimiter.limit(prompt=prompt, max_tokens=max_tokens):
    response = openai.Completion.create(
        model=model_name, prompt=prompt, max_tokens=max_tokens
    )
    ...
```
Note: The rate limits (RPM and TPM) and the Redis host and port provided in the examples are not universal and should be tailored to your specific use case. Please adjust these parameters in accordance with the selected model and your account's rate limits. To find your specific rate limits, please refer to your OpenAI [account settings at OpenAI Rate Limits](https://platform.openai.com/account/rate-limits).

### DalleLimiter

```python
from openai_ratelimiter import DalleLimiter
import openai
import redis

redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )

openai.api_key = "{your API key}"
model_name = "dall-e-2"
prompt = "Create a vibrant and detailed landscape of Morocco. Include vast desert dunes with a warm golden hue, rugged mountain ranges in the background, and traditional Moroccan architecture such as adobe houses and intricate tile work. Add a clear blue sky with a few fluffy clouds, and perhaps a camel caravan in the distance to evoke the essence of Morocco’s unique scenery and culture."

imglimiter = DalleLimiter(
    model_name=model_name,
    IPM=5,
    redis_instance = redis_instance,
)
with imglimiter.limit():
    response = client.images.generate(
    model=model_name, 
    prompt=prompt,   
    size="1024x1024",
    quality="standard",
    n=1,
    )
    ...
```



## Available Methods for Limiter Classes 

The following methods are available in all Limiter classes including `ChatCompletionLimiter`, `AsyncChatCompletionLimiter`, `BaseAPILimiterRedis`, and `AsyncBaseAPILimiterRedis`:

#### `clear_locks()`

The `clear_locks()` method is used to remove all locks that are currently associated with the model. This method is useful when you need to manually reset the lock state.

Usage:

```python
limiter = AsyncChatCompletionLimiter(
        model_name=model_name,
        RPM=3_000,  
        TPM=180_000,  
        redis_instance=redis_instance
    )
success = limiter.clear_locks()
```

In this example, `success` will be `True` if the locks were cleared successfully, otherwise it will be `False`.

#### `is_locked(messages: List[Dict[str, str]], max_tokens: int)`

The `is_locked()` method is used to check if the request would be locked given the specified messages and max tokens.

Usage:

```python
limiter = AsyncChatCompletionLimiter(
        model_name=model_name,
        RPM=3_000,  
        TPM=180_000,  
        redis_instance=redis_instance
    )
messages = [{"role": "system", "content": "You are a helpful assistant."}]
max_tokens = 200
lock_state = limiter.is_locked(messages=messages, max_tokens=max_tokens)
```

In this example, `lock_state` will be `True` if the request would be locked given the messages and max tokens, otherwise it will be `False`.

This should provide users with a clear understanding of how to use the `clear_locks` and `is_locked` methods with any of the Limiter classes.
## Asynchronous Programming Support

This library also provides support for asynchronous programming with two classes: `AsyncChatCompletionLimiter` and `AsyncTextCompletionLimiter`. You can import these classes as follows:

```python
from openai_ratelimiter.asyncio import AsyncChatCompletionLimiter, AsyncTextCompletionLimiter
```

The methods for these classes are the same as their synchronous counterparts. However, the context managers for these classes are asynchronous and must run within an async function.

Here are some examples of how to use these classes:

### AsyncChatCompletionLimiter

- To use **redis** as the caching service:
```python
import asyncio
import openai
from openai_ratelimiter.asyncio import AsyncChatCompletionLimiter
import redis.asyncio as redis

redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )

openai.api_key = "{Openai API key}"
model_name = "gpt-3.5-turbo-16k"
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of Morocco."},
]
max_tokens = 175
chatlimiter = AsyncChatCompletionLimiter(
    model_name=model_name,
    RPM=3_500,
    TPM=180_000,
    redis_instance = redis_instance,
)

async def send_request():
    async with chatlimiter.limit(messages=messages, max_tokens=max_tokens):
        response = await openai.ChatCompletion.acreate(
            model=model_name, messages=messages, max_tokens=max_tokens
        )
        # process response here...

async def main():
    async with asyncio.TaskGroup() as tg:
        for _ in range(100):
            tg.create_task(send_request())

asyncio.run(main())
```

- To use **in-memory** caching:
```python
import asyncio
import openai
from openai_ratelimiter.asyncio import AsyncChatCompletionLimiter


openai.api_key = "{Openai API key}"
model_name = "gpt-3.5-turbo-16k"
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of Morocco."},
]
max_tokens = 175
chatlimiter = AsyncChatCompletionLimiter(
    model_name=model_name,
    RPM=3_500,
    TPM=180_000,
)

async def send_request():
    async with chatlimiter.limit(messages=messages, max_tokens=max_tokens):
        response = await openai.ChatCompletion.acreate(
            model=model_name, messages=messages, max_tokens=max_tokens
        )
        # process response here...

async def main():
    async with asyncio.TaskGroup() as tg:
        for _ in range(100):
            tg.create_task(send_request())

asyncio.run(main())
```


### AsyncTextCompletionLimiter

```python
import asyncio
import openai
from openai_ratelimiter.asyncio import AsyncTextCompletionLimiter
import redis.asyncio as redis

redis_instance = redis.Redis(
        host="localhost",
        port=6379,
    )

openai.api_key = "{OpenAI API key}"
model_name = "text-davinci-003"
prompt = "What is the capital of Morocco."
max_tokens = 200

textlimiter = AsyncTextCompletionLimiter(
    model_name=model_name,
    RPM=3_500,
    TPM=180_000,
    redis_instance=redis_instance

)

async def send_request(_):
    async with textlimiter.limit(prompt=prompt, max_tokens=max_tokens):
        print(_)
        response = await openai.Completion.acreate(
            model=model_name, prompt=prompt, max_tokens=max_tokens
        )
        # process response here...

async def main():
    async with asyncio.TaskGroup() as tg:
        for _ in range(100):
            tg.create_task(send_request(_))

asyncio.run(main())
```

Note: The rate limits (RPM and TPM) and the Redis host and port provided in the examples are not universal and should be tailored to your specific use case. Please adjust these parameters in accordance with the selected model and your account's rate limits. To find your specific rate limits, please refer to your [OpenAI account settings at OpenAI Rate Limits](https://platform.openai.com/account/rate-limits).


## Future Plans

- Support for new OpenAI features (Function calling,...)
- Limiting for embeddings
- Implementing more functions that provide information about the current state
- Implement limiting for the organization level.
- Langchain support.
## Completed plans
- Limiting for DALL·E image model ✅
- In-memory caching ✅
## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue on the GitHub repository. Before contributing, make sure to read through any contributing guidelines and adhere to the code of conduct.

## Legal Disclaimer

This project is not affiliated, associated, authorized, endorsed by, or in any way officially connected with OpenAI, or any of its subsidiaries or affiliates. The official OpenAI website can be found at https://openai.com.

## Author

This library is created and maintained by Youssef Benhammouda. If you have any questions or feedback, you can reach out to him through the GitHub repository.
