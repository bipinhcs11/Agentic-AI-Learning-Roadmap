package com.example.userdelegation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

class DelegationPolicyTest {
    private final DelegationPolicy policy = new DelegationPolicy();

    @Test
    void mapsOnlyExplicitRolesToDelegableScopes() {
        Map<String, Object> claims = Map.of(
                "realm_access", Map.of("roles", List.of(
                        "offline_access", "invoice-reader", "email-drafter")));
        assertThat(policy.delegableScopes(claims))
                .containsExactly("email.draft", "invoice.read");
    }

    @Test
    void rejectsPermissionTheUserDoesNotHave() {
        Map<String, Object> claims = Map.of(
                "realm_access", Map.of("roles", List.of("invoice-reader")));
        assertThatThrownBy(() -> policy.authorize(claims, Set.of("invoice.approve")))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("not allowed");
    }
}
