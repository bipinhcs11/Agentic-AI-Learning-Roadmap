package com.example.aiidentity.api;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;

public final class AgentApiModels {
    private AgentApiModels() {}

    public record RegisterAgentRequest(
            @NotBlank @Size(max = 120) String displayName,
            @NotBlank @Size(max = 120) String ownerId,
            @NotBlank @Size(max = 120) String tenantId,
            @NotEmpty @Size(max = 20) Set<@Pattern(regexp = "[a-z][a-z0-9.-]{1,80}") String> scopes) {}

    public record AgentResponse(
            UUID id,
            String displayName,
            String ownerId,
            String tenantId,
            Set<String> scopes,
            String status,
            String auditId,
            Instant createdAt) {}

    public record AgentStatusResponse(UUID id, String status, boolean active) {}

    public record TokenRequest(
            @NotNull UUID agentId,
            @NotEmpty Set<String> requestedScopes,
            @NotBlank String audience,
            @Min(60) @Max(3600) Integer ttlSeconds) {}

    public record TaskTokenRequest(
            @NotNull UUID agentId,
            @NotBlank String taskId,
            @NotBlank String actorId,
            @NotEmpty Set<String> requestedScopes,
            @NotBlank String audience,
            @Min(60) @Max(600) Integer ttlSeconds,
            @Min(0) @Max(4) Integer delegationDepth) {}

    public record TokenResponse(
            String tokenType,
            String accessToken,
            long expiresIn,
            String scope,
            String auditId) {}

    public record RevokeAgentRequest(@NotNull UUID agentId, @NotBlank @Size(max = 200) String reason) {}

    public record RevokeAgentResponse(UUID agentId, String status, String auditId) {}

    public record TaskStatusResponse(String taskId, UUID agentId, boolean active) {}

    public record RevokeTaskRequest(
            @NotBlank String taskId,
            @NotNull UUID agentId,
            @NotBlank @Size(max = 200) String reason) {}

    public record RevokeTaskResponse(String taskId, UUID agentId, String status, String auditId) {}
}
