package com.example.userdelegation;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class DelegationPolicy {
    private static final Map<String, String> ROLE_TO_SCOPE = Map.of(
            "invoice-reader", "invoice.read",
            "email-drafter", "email.draft");

    public Set<String> delegableScopes(Map<String, Object> claims) {
        Object realmAccess = claims.get("realm_access");
        if (!(realmAccess instanceof Map<?, ?> access)) {
            return Set.of();
        }
        Object rolesObject = access.get("roles");
        if (!(rolesObject instanceof Collection<?> roles)) {
            return Set.of();
        }
        LinkedHashSet<String> scopes = new LinkedHashSet<>();
        roles.stream().map(Object::toString).sorted().forEach(role -> {
            String scope = ROLE_TO_SCOPE.get(role);
            if (scope != null) scopes.add(scope);
        });
        return scopes;
    }

    public Set<String> authorize(Map<String, Object> claims, Set<String> requestedScopes) {
        Set<String> allowed = delegableScopes(claims);
        if (requestedScopes.isEmpty() || !allowed.containsAll(requestedScopes)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "User is not allowed to delegate every requested scope");
        }
        return new LinkedHashSet<>(requestedScopes.stream().sorted().toList());
    }
}
