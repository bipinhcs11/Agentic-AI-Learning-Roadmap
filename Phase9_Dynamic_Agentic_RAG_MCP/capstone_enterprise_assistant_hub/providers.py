"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | providers.py                                          ║
║  One generation interface for Ollama, Bedrock, SageMaker, and Hugging Face. ║
║                                                                              ║
║  WHY: the hub can run locally on a Mac with Ollama, then switch to a cloud   ║
║  runtime with one env var. Cloud SDKs are loaded only when their runtime     ║
║  path is used, so imports and tests never need AWS or Hugging Face creds.    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Completion:
        ...

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def estimate_tokens(text: str) -> int:
    return max(1, len((text or "").split()) * 4 // 3)


def _messages_text(messages: list[dict]) -> str:
    return "\n\n".join(str(m.get("content", "")) for m in messages)


def _last_user_text(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return _messages_text(messages)


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA DEFAULT
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.model = os.getenv("AI_MODEL", "qwen2.5:3b")
        self._client = None

    def _openai_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )
        return self._client

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Completion:
        response = self._openai_client().chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        return Completion(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", None) or estimate_tokens(_messages_text(messages)),
            output_tokens=getattr(usage, "completion_tokens", None) or estimate_tokens(text),
            model=self.model,
        )

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        stream = self._openai_client().chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ═══════════════════════════════════════════════════════════════════════════════
# AWS BEDROCK
# ═══════════════════════════════════════════════════════════════════════════════

class BedrockProvider:
    name = "bedrock"

    def __init__(self) -> None:
        self.model = os.environ["BEDROCK_MODEL_ID"]
        self._client = None

    def _bedrock_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "bedrock-runtime",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        return self._client

    @staticmethod
    def _to_bedrock(messages: list[dict]) -> tuple[list[dict], list[dict]]:
        system = [{"text": m["content"]} for m in messages if m.get("role") == "system"]
        chat_messages = [
            {"role": m.get("role", "user"), "content": [{"text": m.get("content", "")}]}
            for m in messages
            if m.get("role") != "system"
        ]
        return system, chat_messages

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Completion:
        system, chat_messages = self._to_bedrock(messages)
        kwargs = {
            "modelId": self.model,
            "messages": chat_messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = system
        response = self._bedrock_client().converse(**kwargs)
        text = response["output"]["message"]["content"][0]["text"].strip()
        usage = response.get("usage", {})
        return Completion(
            text=text,
            input_tokens=usage.get("inputTokens", estimate_tokens(_messages_text(messages))),
            output_tokens=usage.get("outputTokens", estimate_tokens(text)),
            model=self.model,
        )

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        system, chat_messages = self._to_bedrock(messages)
        kwargs = {
            "modelId": self.model,
            "messages": chat_messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = system
        response = self._bedrock_client().converse_stream(**kwargs)
        for event in response["stream"]:
            delta = event.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
            if delta:
                yield delta


# ═══════════════════════════════════════════════════════════════════════════════
# AWS SAGEMAKER
# ═══════════════════════════════════════════════════════════════════════════════

class SageMakerProvider:
    name = "sagemaker"

    def __init__(self) -> None:
        self.model = os.environ["SAGEMAKER_ENDPOINT_NAME"]
        self._client = None

    def _sagemaker_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "sagemaker-runtime",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        return self._client

    @staticmethod
    def _flatten(messages: list[dict]) -> str:
        return "\n\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages) + "\n\nassistant:"

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Completion:
        prompt = self._flatten(messages)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": max(temperature, 0.01),
                "return_full_text": False,
            },
        }
        response = self._sagemaker_client().invoke_endpoint(
            EndpointName=self.model,
            ContentType="application/json",
            Body=json.dumps(payload),
        )
        body = json.loads(response["Body"].read())
        if isinstance(body, list):
            text = body[0].get("generated_text", "").strip()
        else:
            text = body.get("generated_text", "").strip()
        return Completion(
            text=text,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text),
            model=self.model,
        )

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        prompt = self._flatten(messages)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": max(temperature, 0.01),
                "return_full_text": False,
            },
        }
        try:
            response = self._sagemaker_client().invoke_endpoint_with_response_stream(
                EndpointName=self.model,
                ContentType="application/json",
                Body=json.dumps(payload),
            )
            for event in response["Body"]:
                raw = event.get("PayloadPart", {}).get("Bytes", b"").decode("utf-8", "ignore")
                for line in raw.splitlines():
                    line = line.removeprefix("data:").strip()
                    if not line or line == "[DONE]":
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = parsed.get("token", {}).get("text") or parsed.get("generated_text", "")
                    if token:
                        yield token
        except Exception:
            yield self.complete(messages, temperature=temperature, max_tokens=max_tokens).text


# ═══════════════════════════════════════════════════════════════════════════════
# HUGGING FACE SERVERLESS INFERENCE
# ═══════════════════════════════════════════════════════════════════════════════

class HFProvider:
    name = "hf"

    def __init__(self) -> None:
        self.model = os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct")
        self.endpoint = os.getenv("HF_INFERENCE_URL", f"https://api-inference.huggingface.co/models/{self.model}")

    def _headers(self) -> dict:
        token = os.getenv("HF_TOKEN", "")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Completion:
        import httpx

        payload = {
            "inputs": _messages_text(messages),
            "parameters": {"max_new_tokens": max_tokens, "temperature": max(temperature, 0.01)},
        }
        response = httpx.post(self.endpoint, headers=self._headers(), json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if isinstance(body, list):
            text = body[0].get("generated_text", "")
        else:
            text = body.get("generated_text", "")
        text = text.strip()
        return Completion(text, estimate_tokens(_last_user_text(messages)), estimate_tokens(text), self.model)

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        yield self.complete(messages, temperature=temperature, max_tokens=max_tokens).text


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_PROVIDERS = {
    "ollama": OllamaProvider,
    "bedrock": BedrockProvider,
    "sagemaker": SageMakerProvider,
    "hf": HFProvider,
}
_cache: dict[str, LLMProvider] = {}


def get_provider() -> LLMProvider:
    key = os.getenv("AI_PROVIDER", "ollama").strip().lower() or "ollama"
    if key not in _PROVIDERS:
        raise ValueError(f"Unknown AI_PROVIDER={key!r}. Choose one of: {', '.join(sorted(_PROVIDERS))}")
    if key not in _cache:
        _cache[key] = _PROVIDERS[key]()
    return _cache[key]


def clear_provider_cache() -> None:
    _cache.clear()
