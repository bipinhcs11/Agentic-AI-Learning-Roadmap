package com.example.userdelegation;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

class PolicyDecisionClientTest {
    private final PolicyDecisionClient client = new PolicyDecisionClient(RestClient.builder(), "");

    @Test
    void localModeRequiresUserAndAgentTenantMatch() {
        assertThatCode(() -> client.authorize(
                Map.of("tenant_id", "fictional-acme"),
                Set.of("invoice.read"),
                "fictional-acme",
                "fictional-invoice-api"))
                .doesNotThrowAnyException();

        assertThatThrownBy(() -> client.authorize(
                Map.of("tenant_id", "fictional-acme"),
                Set.of("invoice.read"),
                "fictional-globex",
                "fictional-invoice-api"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("tenant must match");
    }
}
