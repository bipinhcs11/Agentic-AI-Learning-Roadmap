package com.example.aiidentity.service;

import static com.example.aiidentity.api.AgentApiModels.*;

import com.example.aiidentity.agent.AgentRegistration;
import com.example.aiidentity.agent.AgentRepository;
import com.nimbusds.jose.jwk.RSAKey;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AgentIdentityService {
    private final AgentRepository repository;
    private final JwtEncoder encoder;
    private final RSAKey rsaKey;
    private final TaskStateStore taskStateStore;
    private final String issuer;

    public AgentIdentityService(
            AgentRepository repository,
            JwtEncoder encoder,
            RSAKey rsaKey,
            TaskStateStore taskStateStore,
            @Value("${identity.issuer}") String issuer) {
        this.repository = repository;
        this.encoder = encoder;
        this.rsaKey = rsaKey;
        this.taskStateStore = taskStateStore;
        this.issuer = issuer;
    }

    @Transactional
    public AgentResponse register(RegisterAgentRequest request) {
        AgentRegistration registration = new AgentRegistration(
                UUID.randomUUID(),
                request.displayName(),
                request.ownerId(),
                request.tenantId(),
                normalizedScopes(request.scopes()),
                UUID.randomUUID().toString(),
                Instant.now());
        return response(repository.save(registration));
    }

    @Transactional(readOnly = true)
    public AgentResponse get(UUID id) {
        return response(find(id));
    }

    @Transactional(readOnly = true)
    public AgentStatusResponse status(UUID id) {
        AgentRegistration agent = find(id);
        return new AgentStatusResponse(agent.getId(), agent.getStatus(), agent.isActive());
    }

    @Transactional(readOnly = true)
    public TokenResponse issueAgentToken(TokenRequest request) {
        int ttl = request.ttlSeconds() == null ? 900 : request.ttlSeconds();
        return issue(
                findActive(request.agentId()),
                request.requestedScopes(),
                request.audience(),
                ttl,
                Map.of("credential_type", "agent"));
    }

    @Transactional(readOnly = true)
    public TokenResponse issueTaskToken(TaskTokenRequest request) {
        int ttl = request.ttlSeconds() == null ? 600 : request.ttlSeconds();
        int depth = request.delegationDepth() == null ? 0 : request.delegationDepth();
        AgentRegistration agent = findActive(request.agentId());
        validateScopes(agent, request.requestedScopes());
        try {
            taskStateStore.activate(request.taskId(), agent.getId(), Duration.ofSeconds(ttl));
        } catch (IllegalStateException exception) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, exception.getMessage());
        }
        return issue(
                agent,
                request.requestedScopes(),
                request.audience(),
                ttl,
                Map.of(
                        "credential_type", "task",
                        "task_id", request.taskId(),
                        "actor_id", request.actorId(),
                        "delegation_depth", depth));
    }

    @Transactional(readOnly = true)
    public TaskStatusResponse taskStatus(String taskId, UUID agentId) {
        return new TaskStatusResponse(taskId, agentId, taskStateStore.isActive(taskId, agentId));
    }

    public RevokeTaskResponse revokeTask(RevokeTaskRequest request) {
        taskStateStore.revoke(request.taskId(), request.agentId());
        return new RevokeTaskResponse(
                request.taskId(), request.agentId(), "REVOKED", UUID.randomUUID().toString());
    }

    @Transactional
    public RevokeAgentResponse revoke(RevokeAgentRequest request) {
        AgentRegistration agent = find(request.agentId());
        agent.revoke();
        repository.save(agent);
        return new RevokeAgentResponse(agent.getId(), agent.getStatus(), UUID.randomUUID().toString());
    }

    public Map<String, Object> publicJwks() {
        return new com.nimbusds.jose.jwk.JWKSet(rsaKey.toPublicJWK()).toJSONObject();
    }

    private TokenResponse issue(
            AgentRegistration agent,
            Set<String> requestedScopes,
            String audience,
            int ttlSeconds,
            Map<String, Object> additionalClaims) {
        Set<String> scopes = normalizedScopes(requestedScopes);
        validateScopes(agent, scopes);

        Instant now = Instant.now();
        String auditId = UUID.randomUUID().toString();
        JwtClaimsSet.Builder claims = JwtClaimsSet.builder()
                .issuer(issuer)
                .subject("agent:" + agent.getId())
                .audience(java.util.List.of(audience))
                .issuedAt(now)
                .notBefore(now)
                .expiresAt(now.plus(ttlSeconds, ChronoUnit.SECONDS))
                .id(UUID.randomUUID().toString())
                .claim("agent_id", agent.getId().toString())
                .claim("owner_id", agent.getOwnerId())
                .claim("tenant_id", agent.getTenantId())
                .claim("scope", String.join(" ", scopes))
                .claim("audit_id", auditId);
        additionalClaims.forEach(claims::claim);

        JwsHeader header = JwsHeader.with(SignatureAlgorithm.RS256)
                .keyId(rsaKey.getKeyID())
                .build();
        String token = encoder.encode(JwtEncoderParameters.from(header, claims.build())).getTokenValue();
        return new TokenResponse("Bearer", token, ttlSeconds, String.join(" ", scopes), auditId);
    }

    private AgentRegistration find(UUID id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Agent not found"));
    }

    private AgentRegistration findActive(UUID id) {
        AgentRegistration agent = find(id);
        if (!agent.isActive()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Agent is revoked");
        }
        return agent;
    }

    private static Set<String> normalizedScopes(Set<String> scopes) {
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        scopes.stream().map(String::trim).sorted().forEach(normalized::add);
        return normalized;
    }

    private static void validateScopes(AgentRegistration agent, Set<String> requestedScopes) {
        Set<String> scopes = normalizedScopes(requestedScopes);
        if (!agent.getAllowedScopes().containsAll(scopes)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Requested scopes exceed the agent allow-list");
        }
    }

    private static AgentResponse response(AgentRegistration agent) {
        return new AgentResponse(
                agent.getId(),
                agent.getDisplayName(),
                agent.getOwnerId(),
                agent.getTenantId(),
                agent.getAllowedScopes(),
                agent.getStatus(),
                agent.getRegistrationAuditId(),
                agent.getCreatedAt());
    }
}
