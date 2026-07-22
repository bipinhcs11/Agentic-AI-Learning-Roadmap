package com.example.securemcp;

import java.util.Collection;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
class ToolAuthorizer {
    private final AuditService auditService;
    private final TaskStatusVerifier taskStatusVerifier;
    private final int maxDelegationDepth;

    ToolAuthorizer(
            AuditService auditService,
            TaskStatusVerifier taskStatusVerifier,
            @Value("${mcp-security.max-delegation-depth}") int maxDelegationDepth) {
        this.auditService = auditService;
        this.taskStatusVerifier = taskStatusVerifier;
        this.maxDelegationDepth = maxDelegationDepth;
    }

    SecurityContext authorize(String tool, Set<String> requiredScopes, String resourceTenant) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (!(authentication instanceof JwtAuthenticationToken jwtAuthentication)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "A verified JWT is required");
        }
        var jwt = jwtAuthentication.getToken();
        SecurityContext context = new SecurityContext(
                jwt.getSubject(),
                jwt.getClaimAsString("tenant_id"),
                jwt.getClaimAsString("task_id"),
                jwt.getClaimAsString("audit_id"));

        denyUnless("task".equals(jwt.getClaimAsString("credential_type")), tool, context,
                "A task credential is required");
        denyUnless(context.taskId() != null && !context.taskId().isBlank(), tool, context,
                "Task identifier is required");
        String agentId = jwt.getClaimAsString("agent_id");
        denyUnless(agentId != null && taskStatusVerifier.isActive(agentId, context.taskId()), tool, context,
                "Agent or task is revoked, expired, or unavailable");
        Integer depth = jwt.getClaim("delegation_depth");
        denyUnless(depth == null || depth <= maxDelegationDepth, tool, context,
                "Delegation depth exceeds policy");
        Object rawScopes = jwt.getClaim("scope");
        Set<String> tokenScopes = rawScopes instanceof Collection<?> values
                ? values.stream().map(Object::toString).collect(java.util.stream.Collectors.toUnmodifiableSet())
                : Set.copyOf(splitScopes(rawScopes == null ? null : rawScopes.toString()));
        denyUnless(tokenScopes.containsAll(requiredScopes), tool, context,
                "Tool is outside the credential scope allow-list");
        denyUnless(resourceTenant == null || resourceTenant.equals(context.tenantId()), tool, context,
                "Tenant boundary denied the resource");

        auditService.record("ALLOW", tool, context.subject(), context.tenantId(),
                context.taskId(), context.auditId(), "policy requirements satisfied");
        return context;
    }

    private void denyUnless(boolean condition, String tool, SecurityContext context, String reason) {
        if (!condition) {
            auditService.record("DENY", tool, context.subject(), context.tenantId(),
                    context.taskId(), context.auditId(), reason);
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, reason);
        }
    }

    private static Collection<String> splitScopes(String scopes) {
        return scopes == null || scopes.isBlank() ? Set.of() : Set.of(scopes.split(" "));
    }

    record SecurityContext(String subject, String tenantId, String taskId, String auditId) {}
}
