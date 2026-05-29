"""LLM connectors for Anthropic Claude and Mistral AI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Generator

import anthropic
from mistralai import Mistral

ANTHROPIC_MODELS = [
    ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
    ("claude-haiku-4-20250414", "Claude Haiku 4"),
]

MISTRAL_MODELS = [
    ("mistral-large-latest", "Mistral Large"),
    ("mistral-small-latest", "Mistral Small"),
    ("open-mistral-nemo", "Mistral Nemo (Open)"),
]


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int


def _get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")
    return anthropic.Anthropic(api_key=api_key)


def _get_mistral_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set. Add it to your .env file.")
    return Mistral(api_key=api_key)


def stream_anthropic(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 16384,
) -> Generator[str, None, None]:
    client = _get_anthropic_client()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def stream_mistral(
    system_prompt: str,
    user_message: str,
    model: str = "mistral-large-latest",
    max_tokens: int = 16384,
) -> Generator[str, None, None]:
    client = _get_mistral_client()
    response = client.chat.stream(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    for event in response:
        chunk = event.data.choices[0].delta.content
        if chunk:
            yield chunk


def stream(
    system_prompt: str,
    user_message: str,
    provider: str = "anthropic",
    model: str | None = None,
    max_tokens: int = 16384,
) -> Generator[str, None, None]:
    if provider == "anthropic":
        yield from stream_anthropic(
            system_prompt,
            user_message,
            model=model or ANTHROPIC_MODELS[0][0],
            max_tokens=max_tokens,
        )
    elif provider == "mistral":
        yield from stream_mistral(
            system_prompt,
            user_message,
            model=model or MISTRAL_MODELS[0][0],
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
