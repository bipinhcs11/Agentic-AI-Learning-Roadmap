from __future__ import annotations

import importlib
import io
import sys
import types

import pytest


def reload_providers(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    if "providers" in sys.modules:
        return importlib.reload(sys.modules["providers"])
    return importlib.import_module("providers")


def test_default_provider_does_not_import_boto3(monkeypatch):
    sys.modules.pop("boto3", None)
    providers = reload_providers(monkeypatch)
    providers.clear_provider_cache()

    provider = providers.get_provider()

    assert provider.name == "ollama"
    assert "boto3" not in sys.modules


def test_bad_provider_value_errors(monkeypatch):
    providers = reload_providers(monkeypatch)
    providers.clear_provider_cache()
    monkeypatch.setenv("AI_PROVIDER", "bad")

    with pytest.raises(ValueError):
        providers.get_provider()


def test_bedrock_provider_mocked(monkeypatch):
    providers = reload_providers(monkeypatch)
    providers.clear_provider_cache()

    fake_runtime = types.SimpleNamespace()
    fake_runtime.converse = lambda **_: {
        "output": {"message": {"content": [{"text": "bedrock ok"}]}},
        "usage": {"inputTokens": 5, "outputTokens": 2},
    }
    fake_runtime.converse_stream = lambda **_: {
        "stream": [
            {"contentBlockDelta": {"delta": {"text": "bed"}}},
            {"contentBlockDelta": {"delta": {"text": "rock"}}},
        ]
    }
    fake_boto3 = types.SimpleNamespace(client=lambda *_, **__: fake_runtime)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("AI_PROVIDER", "bedrock")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "model-x")

    provider = providers.get_provider()
    out = provider.complete([{"role": "user", "content": "hello"}])

    assert provider.name == "bedrock"
    assert out.text == "bedrock ok"
    assert out.input_tokens == 5
    assert "".join(provider.stream([{"role": "user", "content": "hello"}])) == "bedrock"


def test_sagemaker_provider_mocked(monkeypatch):
    providers = reload_providers(monkeypatch)
    providers.clear_provider_cache()

    fake_runtime = types.SimpleNamespace()
    fake_runtime.invoke_endpoint = lambda **_: {
        "Body": io.BytesIO(b'[{"generated_text": "sagemaker ok"}]')
    }
    fake_boto3 = types.SimpleNamespace(client=lambda *_, **__: fake_runtime)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("AI_PROVIDER", "sagemaker")
    monkeypatch.setenv("SAGEMAKER_ENDPOINT_NAME", "endpoint-x")

    provider = providers.get_provider()
    out = provider.complete([{"role": "user", "content": "hello"}])

    assert provider.name == "sagemaker"
    assert out.text == "sagemaker ok"


def test_hf_provider_selection_has_no_network_call(monkeypatch):
    providers = reload_providers(monkeypatch)
    providers.clear_provider_cache()
    monkeypatch.setenv("AI_PROVIDER", "hf")

    provider = providers.get_provider()

    assert provider.name == "hf"
