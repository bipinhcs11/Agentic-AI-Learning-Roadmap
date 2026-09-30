"""Sanitized error types shared by gateway and scenario servers."""


class EnterpriseMcpError(RuntimeError):
    """Base error safe to map to a bounded MCP tool failure."""

    code = "ENTERPRISE_MCP_ERROR"


class ConfigurationError(EnterpriseMcpError):
    code = "CONFIGURATION_ERROR"


class SecretRetrievalError(EnterpriseMcpError):
    code = "SECRET_RETRIEVAL_FAILED"


class TokenAcquisitionError(EnterpriseMcpError):
    code = "TOKEN_ACQUISITION_FAILED"


class UpstreamApiError(EnterpriseMcpError):
    code = "UPSTREAM_API_FAILED"


class PolicyDeniedError(EnterpriseMcpError):
    code = "POLICY_DENIED"
