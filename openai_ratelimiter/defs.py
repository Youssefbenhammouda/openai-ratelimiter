from typing import Any, Dict, List, Union

from .base import CL100K_ENCODER, P50K_ENCODER, BaseAPILimiterRedis


def num_tokens_consumed_by_chat_request(
    messages: List[Dict[str, str]], max_tokens: int = 15, n: int = 1
):
    num_tokens = n * max_tokens
    for message in messages:
        num_tokens += (
            4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        )
        for key, value in message.items():
            num_tokens += len(CL100K_ENCODER.encode(value))

            if key == "name":  # If there's a name, the role is omitted
                num_tokens -= 1

    num_tokens += 2  # Every reply is primed with <im_start>assistant

    return num_tokens


def num_tokens_consumed_by_completion_request(
    prompt: Union[str, list[str], Any], max_tokens: int = 15, n: int = 1
):
    num_tokens = n * max_tokens
    if isinstance(prompt, str):  # Single prompt
        num_tokens += len(P50K_ENCODER.encode(prompt))
    elif isinstance(prompt, list):  # Multiple prompts
        num_tokens *= len(prompt)
        num_tokens += sum([len([P50K_ENCODER.encode(p) for p in prompt])])
    else:
        raise TypeError(
            "Either a string or list of strings expected for 'prompt' field in completion request."
        )

    return num_tokens


class ChatCompletionLimiter(BaseAPILimiterRedis):
    def limit(self, messages: List[Dict[str, str]], max_tokens: int):
        tokens = num_tokens_consumed_by_chat_request(messages, max_tokens)
        return self._limit(tokens)

    def is_locked(self, messages: List[Dict[str, str]], max_tokens: int) -> bool:
        """Returns True if the request would be locked, False otherwise."""
        tokens = num_tokens_consumed_by_chat_request(messages, max_tokens)
        return self._is_locked(tokens)


class TextCompletionLimiter(BaseAPILimiterRedis):
    def limit(self, prompt: str, max_tokens: int):
        tokens = num_tokens_consumed_by_completion_request(prompt, max_tokens)
        return self._limit(tokens)

    def is_locked(self, prompt: str, max_tokens: int) -> bool:
        tokens = num_tokens_consumed_by_completion_request(prompt, max_tokens)
        return self._is_locked(tokens)
