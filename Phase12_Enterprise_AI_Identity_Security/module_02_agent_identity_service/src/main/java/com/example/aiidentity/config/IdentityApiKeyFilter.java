package com.example.aiidentity.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
class IdentityApiKeyFilter extends OncePerRequestFilter {
    private final String adminToken;
    private final String brokerToken;
    private final String statusToken;

    IdentityApiKeyFilter(
            @Value("${identity.admin-token}") String adminToken,
            @Value("${identity.broker-token}") String brokerToken,
            @Value("${identity.status-token}") String statusToken) {
        this.adminToken = adminToken;
        this.brokerToken = brokerToken;
        this.statusToken = statusToken;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        String expected = expectedToken(request.getMethod(), request.getRequestURI());
        if (expected == null || constantTimeEquals(expected, request.getHeader("X-Identity-Token"))) {
            filterChain.doFilter(request, response);
            return;
        }
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.getWriter().write("{\"status\":401,\"error\":\"Valid identity service credential required\"}");
    }

    private String expectedToken(String method, String path) {
        if ("GET".equals(method) && path.equals("/actuator/health")) return null;
        if ("GET".equals(method) && path.equals("/.well-known/jwks.json")) return null;
        if ("POST".equals(method) && (path.equals("/agent/register")
                || path.equals("/agent/revoke") || path.equals("/task/revoke"))) return adminToken;
        if ("POST".equals(method) && (path.equals("/agent/token")
                || path.equals("/agent/task-token"))) return brokerToken;
        if ("GET".equals(method) && (path.startsWith("/agent/") || path.startsWith("/task/"))) {
            return statusToken;
        }
        return adminToken;
    }

    private static boolean constantTimeEquals(String expected, String actual) {
        if (actual == null) return false;
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                actual.getBytes(StandardCharsets.UTF_8));
    }
}
