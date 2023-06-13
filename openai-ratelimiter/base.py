import time

import redis
import tiktoken
from redis.lock import Lock

# Tokenizer
CL100K_ENCODER = tiktoken.get_encoding("cl100k_base")
P50K_ENCODER = tiktoken.get_encoding("p50k_base")
period = 60


class Limiter:
    def __init__(self, model_name, max_calls, max_tokens, period, tokens, redis):
        self.model_name = model_name
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.period = period
        self.tokens = tokens
        self.redis = redis

    def __enter__(self):
        lock = Lock(self.redis, f"{self.model_name}_lock", timeout=self.period)

        with lock:
            while True:
                self.current_calls = self.redis.incr(
                    f"{self.model_name}_api_calls", amount=1
                )
                if self.current_calls == 1:
                    self.redis.expire(f"{self.model_name}_api_calls", self.period)
                if self.current_calls <= self.max_calls:
                    break
                else:
                    time.sleep(self.period)  # wait for the limit to reset

            while True:
                self.current_tokens = self.redis.incrby(
                    f"{self.model_name}_api_tokens", self.tokens
                )
                if self.current_tokens == self.tokens:
                    self.redis.expire(f"{self.model_name}_api_tokens", self.period)
                if self.current_tokens <= self.max_tokens:
                    break
                else:
                    time.sleep(self.period)  # wait for the limit to reset

    def __exit__(self, type, value, traceback):
        pass


class __BaseAPILimiterRedis:
    def __init__(
        self,
        model_name,
        RPM: int,
        TPM: int,
        redis_host="localhost",
        redis_port=6379,
    ):
        self.model_name = model_name
        self.max_calls = RPM
        self.max_tokens = TPM
        self.period = period
        self.redis = redis.Redis(host=redis_host, port=redis_port)

    def _limit(self, tokens):
        return Limiter(
            self.model_name,
            self.max_calls,
            self.max_tokens,
            self.period,
            tokens,
            self.redis,
        )
