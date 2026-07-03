package com.benefits.adk.streaming;

import java.time.Clock;
import java.util.LinkedHashMap;
import java.util.Map;

public record AgUiEvent(String type, Map<String, Object> fields) {
    public Map<String, Object> asProtocolMap(Clock clock) {
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("type", type);
        event.put("timestamp", clock.instant().toEpochMilli());
        event.putAll(fields);
        return event;
    }
}
