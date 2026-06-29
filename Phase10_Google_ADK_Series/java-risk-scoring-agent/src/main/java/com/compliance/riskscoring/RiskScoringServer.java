package com.compliance.riskscoring;

import com.compliance.riskscoring.handler.AgentCardHandler;
import com.compliance.riskscoring.handler.JsonRpcHandler;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.Executors;

/**
 * Main entry point for the Financial Risk Scoring Engine.
 *
 * A lightweight A2A-compliant agent server built on Java's built-in HttpServer
 * (no Spring Boot). Mirrors the Go compliance agent's architecture:
 *   - Agent Card at GET /.well-known/agent.json
 *   - JSON-RPC 2.0 endpoint at POST /
 *   - CORS support on all responses
 *   - Graceful shutdown via SIGTERM/SIGINT
 *
 * Port 9999 by default, configurable via PORT env var or -port flag.
 */
public class RiskScoringServer {

    private static final String DEFAULT_PORT = "9999";
    private static final String DEFAULT_AGENT_URL = "http://localhost:9999";

    public static void main(String[] args) throws IOException {
        // Parse port from args or env
        String port = System.getenv("PORT");
        if (port == null || port.isBlank()) {
            port = DEFAULT_PORT;
        }
        for (int i = 0; i < args.length; i++) {
            if ("-port".equals(args[i]) && i + 1 < args.length) {
                port = args[i + 1];
            }
        }

        int portNum;
        try {
            portNum = Integer.parseInt(port);
        } catch (NumberFormatException e) {
            System.err.println("[ERROR] Invalid port: " + port);
            System.exit(1);
            return;
        }

        // Resolve agent URL for the agent card
        String agentUrl = System.getenv("AGENT_URL");
        if (agentUrl == null || agentUrl.isBlank()) {
            agentUrl = DEFAULT_AGENT_URL;
        }

        // Resolve bind host
        String host = System.getenv("HOST");
        if (host == null || host.isBlank()) {
            host = "0.0.0.0";
        }

        // Configure Jackson ObjectMapper
        ObjectMapper mapper = new ObjectMapper();
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        mapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);

        // Create HTTP server
        InetSocketAddress address = new InetSocketAddress(host, portNum);
        HttpServer server = HttpServer.create(address, 0);

        // Register handlers — Agent Card MUST be registered before the root
        // handler so the more specific path takes priority
        server.createContext("/.well-known/agent.json",
                new AgentCardHandler(mapper, agentUrl));
        server.createContext("/",
                new JsonRpcHandler(mapper));

        // Use a thread pool for handling requests
        server.setExecutor(Executors.newFixedThreadPool(
                Runtime.getRuntime().availableProcessors()));

        // Graceful shutdown hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\nReceived termination signal. Shutting down Risk Scoring Engine...");
            server.stop(3); // 3 second grace period
            System.out.println("Risk Scoring Engine stopped.");
        }));

        // Start the server
        System.out.println("--- Java Financial Risk Scoring Engine (A2A Protocol) ---");
        System.out.printf("Agent Card:  http://%s:%d/.well-known/agent.json%n", host, portNum);
        System.out.printf("JSON-RPC:    http://%s:%d/%n", host, portNum);
        System.out.printf("A2A risk scoring engine listening on %s:%d...%n", host, portNum);

        server.start();
    }
}
