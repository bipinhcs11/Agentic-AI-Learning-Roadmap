package com.benefits.adk;

import com.benefits.adk.streaming.BenefitsAgUiEventStream;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.Executors;

public final class BenefitsAgUiStreamServerApp {
    private static final int DEFAULT_PORT = 8091;

    private BenefitsAgUiStreamServerApp() {
    }

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : DEFAULT_PORT;
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        BenefitsAgUiEventStream eventStream = new BenefitsAgUiEventStream();

        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/healthz", exchange -> writeJson(exchange, mapper, Map.of("status", "ok")));
        server.createContext("/ag-ui/runs/benefits-projection", exchange -> {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                addCorsHeaders(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeJson(exchange, mapper, Map.of("error", "Use GET for the demo stream"), 405);
                return;
            }
            writeSse(exchange, mapper, eventStream);
        });
        server.setExecutor(Executors.newSingleThreadExecutor());
        server.start();
        System.out.println("Rung 01D AG-UI stream server running at http://127.0.0.1:" + port);
        System.out.println("Stream: http://127.0.0.1:" + port + "/ag-ui/runs/benefits-projection");
    }

    private static void writeSse(
            HttpExchange exchange,
            ObjectMapper mapper,
            BenefitsAgUiEventStream eventStream
    ) throws IOException {
        addCorsHeaders(exchange);
        exchange.getResponseHeaders().set("Content-Type", "text/event-stream; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-cache");
        exchange.sendResponseHeaders(200, 0);

        try (OutputStream body = exchange.getResponseBody()) {
            for (Map<String, Object> event : eventStream.projectionDemoEvents()) {
                String eventType = String.valueOf(event.get("type"));
                String frame = "event: " + eventType + "\n"
                        + "data: " + mapper.writeValueAsString(event).replace("\n", "") + "\n\n";
                body.write(frame.getBytes(StandardCharsets.UTF_8));
                body.flush();
                sleepBetweenEvents();
            }
        }
    }

    private static void writeJson(HttpExchange exchange, ObjectMapper mapper, Map<String, Object> payload)
            throws IOException {
        writeJson(exchange, mapper, payload, 200);
    }

    private static void writeJson(
            HttpExchange exchange,
            ObjectMapper mapper,
            Map<String, Object> payload,
            int status
    ) throws IOException {
        addCorsHeaders(exchange);
        byte[] body = mapper.writeValueAsBytes(payload);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(body);
        }
    }

    private static void addCorsHeaders(HttpExchange exchange) {
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "http://127.0.0.1:5174");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type");
    }

    private static void sleepBetweenEvents() {
        try {
            Thread.sleep(180);
        } catch (InterruptedException interruptedException) {
            Thread.currentThread().interrupt();
        }
    }
}
