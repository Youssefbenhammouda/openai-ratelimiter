from typing import Dict, List, Union

from .base import CL100K_ENCODER, P50K_ENCODER, __BaseAPILimiterRedis


def num_tokens_consumed_by_chat_request(messages, max_tokens=15, n=1, **kwargs):
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
    prompt: Union[str, list], max_tokens=15, n=1, **kwargs
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


class ChatCompletionLimiter(__BaseAPILimiterRedis):
    def limit(self, messages: List[Dict], max_tokens):
        tokens = num_tokens_consumed_by_chat_request(messages, max_tokens)
        return self._limit(tokens)


class textCompletionLimiter(__BaseAPILimiterRedis):
    def limit(self, prompt: str, max_tokens):
        tokens = num_tokens_consumed_by_completion_request(prompt, max_tokens)
        return self._limit(tokens)
