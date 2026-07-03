package com.benefits.adk.streaming;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BenefitsAgUiEventStreamTest {
    @Test
    void streamsLifecycleTextToolAndStateEvents() {
        Clock clock = Clock.fixed(Instant.parse("2026-07-03T00:00:00Z"), ZoneOffset.UTC);
        List<Map<String, Object>> events = new BenefitsAgUiEventStream(clock).projectionDemoEvents();

        assertEquals("RUN_STARTED", events.get(0).get("type"));
        assertEquals("RUN_FINISHED", events.get(events.size() - 1).get("type"));
        assertTrue(events.stream().anyMatch(event -> "TEXT_MESSAGE_CONTENT".equals(event.get("type"))));
        assertTrue(events.stream().anyMatch(event -> "TOOL_CALL_START".equals(event.get("type"))));
        assertTrue(events.stream().anyMatch(event -> "STATE_SNAPSHOT".equals(event.get("type"))));
        assertTrue(events.stream().allMatch(event -> event.get("timestamp").equals(1783036800000L)));
    }

    @Test
    void stateSnapshotCarriesTrustedA2uiPayload() {
        Map<String, Object> stateEvent = new BenefitsAgUiEventStream().projectionDemoEvents().stream()
                .filter(event -> "STATE_SNAPSHOT".equals(event.get("type")))
                .findFirst()
                .orElseThrow();

        @SuppressWarnings("unchecked")
        Map<String, Object> snapshot = (Map<String, Object>) stateEvent.get("snapshot");
        @SuppressWarnings("unchecked")
        Map<String, Object> payload = (Map<String, Object>) snapshot.get("a2uiPayload");
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) payload.get("metadata");
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) payload.get("data");

        assertEquals("01D", snapshot.get("rung"));
        assertEquals("application/json+a2ui", metadata.get("mimeType"));
        assertEquals("a2ui.phase10.rung01b.v1", data.get("schemaVersion"));
    }
}
