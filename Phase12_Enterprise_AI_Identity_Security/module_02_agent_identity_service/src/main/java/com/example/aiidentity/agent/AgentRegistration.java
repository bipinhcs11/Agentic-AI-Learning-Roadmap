package com.example.aiidentity.agent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "agent_registrations")
public class AgentRegistration {
    @Id
    private UUID id;

    @Column(nullable = false)
    private String displayName;

    @Column(nullable = false)
    private String ownerId;

    @Column(nullable = false)
    private String tenantId;

    @Column(nullable = false, length = 2000)
    private String allowedScopes;

    @Column(nullable = false)
    private String status;

    @Column(nullable = false)
    private String registrationAuditId;

    @Column(nullable = false)
    private Instant createdAt;

    protected AgentRegistration() {}

    public AgentRegistration(
            UUID id,
            String displayName,
            String ownerId,
            String tenantId,
            Set<String> allowedScopes,
            String registrationAuditId,
            Instant createdAt) {
        this.id = id;
        this.displayName = displayName;
        this.ownerId = ownerId;
        this.tenantId = tenantId;
        this.allowedScopes = String.join(" ", allowedScopes);
        this.status = "ACTIVE";
        this.registrationAuditId = registrationAuditId;
        this.createdAt = createdAt;
    }

    public UUID getId() { return id; }
    public String getDisplayName() { return displayName; }
    public String getOwnerId() { return ownerId; }
    public String getTenantId() { return tenantId; }
    public String getStatus() { return status; }
    public String getRegistrationAuditId() { return registrationAuditId; }
    public Instant getCreatedAt() { return createdAt; }

    public Set<String> getAllowedScopes() {
        return allowedScopes.isBlank()
                ? Set.of()
                : new LinkedHashSet<>(Arrays.asList(allowedScopes.split(" ")));
    }

    public boolean isActive() {
        return "ACTIVE".equals(status);
    }

    public void revoke() {
        this.status = "REVOKED";
    }
}
