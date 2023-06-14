
# openai-ratelimiter

openai-ratelimiter is a simple and efficient rate limiter for the OpenAI API. It is designed to help prevent the API rate limit from being reached when using the OpenAI library. Currently, it supports only Redis as the caching service.

## Installation

To install the openai-ratelimiter library, use pip:

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

The library provides two classes, `ChatCompletionLimiter` and `TextCompletionLimiter`, for limiting rate of API calls.

### ChatCompletionLimiter

```python
from openai_ratelimiter import ChatCompletionLimiter
import openai

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
    redis_host="localhost",
    redis_port=6379,
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

openai.api_key = "{your API key}"
model_name = "text-davinci-003"
prompt = "What is the capital of Morocco."
max_tokens = 200
textlimiter = TextCompletionLimiter(
    model_name=model_name,
    RPM=3_000,
    TPM=250_000,
    redis_host="localhost",
    redis_port=6379,
)
with textlimiter.limit(prompt=prompt, max_tokens=max_tokens):
    response = openai.Completion.create(
        model=model_name, prompt=prompt, max_tokens=max_tokens
    )
    ...
```

## Future Plans

- In-memory caching
- Limiting for embeddings
- Limiting for DALL·E image model
- Implementing more functions that provide information about the current state
