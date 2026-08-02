"""Bind registry input contracts to FastMCP discovery and call validation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from jsonschema import Draft202012Validator
from mcp.server.fastmcp import FastMCP

from .registry import RegistrySnapshot


def bind_registry_schemas(mcp: FastMCP, registry: RegistrySnapshot) -> None:
    for registered in registry.catalog():
        tool = mcp._tool_manager._tools.get(registered.name)
        if tool is None:
            raise RuntimeError(f"Registered tool is not implemented: {registered.name}")

        tool.parameters = registered.input_schema
        tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
        tool.fn_metadata.arg_model.model_rebuild(force=True)
        validator = Draft202012Validator(registered.input_schema)
        original: Callable[..., Awaitable[Any]] = tool.fn

        async def validated_call(
            _validator: Draft202012Validator = validator,
            _original: Callable[..., Awaitable[Any]] = original,
            **arguments: Any,
        ) -> Any:
            if next(_validator.iter_errors(arguments), None) is not None:
                raise ValueError("Arguments do not match the approved registry schema")
            return await _original(**arguments)

        tool.fn = validated_call
