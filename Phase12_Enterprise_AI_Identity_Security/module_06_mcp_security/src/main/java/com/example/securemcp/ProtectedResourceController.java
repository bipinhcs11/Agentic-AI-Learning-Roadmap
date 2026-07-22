package com.example.securemcp;

import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class ProtectedResourceController {
    private final String resource;
    private final String authorizationServer;

    ProtectedResourceController(
            @Value("${mcp-security.resource}") String resource,
            @Value("${mcp-security.authorization-server}") String authorizationServer) {
        this.resource = resource;
        this.authorizationServer = authorizationServer;
    }

    @GetMapping("/.well-known/oauth-protected-resource")
    Map<String, Object> metadata() {
        return Map.of(
                "resource", resource,
                "authorization_servers", List.of(authorizationServer),
                "scopes_supported", List.of("invoice.read", "email.draft"),
                "bearer_methods_supported", List.of("header"));
    }
}
