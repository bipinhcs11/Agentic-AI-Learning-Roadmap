package com.benefits.adk.streaming;

import com.benefits.adk.BenefitsConciergeTools;
import java.time.Clock;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class BenefitsAgUiEventStream {
    private final Clock clock;

    public BenefitsAgUiEventStream() {
        this(Clock.systemUTC());
    }

    BenefitsAgUiEventStream(Clock clock) {
        this.clock = clock;
    }

    public List<Map<String, Object>> projectionDemoEvents() {
        String threadId = "phase10-module01";
        String runId = "run-" + UUID.randomUUID();
        String messageId = "msg-" + UUID.randomUUID();
        String toolCallId = "tool-" + UUID.randomUUID();
        Map<String, Object> a2uiPayload = BenefitsConciergeTools.buildProjectionA2uiCard(
                100000,
                6,
                4400,
                "self-only",
                24
        );

        List<AgUiEvent> events = new ArrayList<>();
        events.add(event("RUN_STARTED", Map.of(
                "threadId", threadId,
                "runId", runId,
                "input", Map.of(
                        "prompt", "Build a live fictional benefits projection.",
                        "rung", "01D"
                )
        )));
        events.add(event("STEP_STARTED", Map.of("stepName", "screen_request")));
        events.add(event("STEP_FINISHED", Map.of("stepName", "screen_request")));
        events.add(event("TEXT_MESSAGE_START", Map.of(
                "messageId", messageId,
                "role", "assistant"
        )));
        events.add(event("TEXT_MESSAGE_CONTENT", Map.of(
                "messageId", messageId,
                "delta", "Building a fictional projection from deterministic Java tools. "
        )));
        events.add(event("TEXT_MESSAGE_CONTENT", Map.of(
                "messageId", messageId,
                "delta", "The browser will receive the trusted A2UI card as streamed state."
        )));
        events.add(event("TEXT_MESSAGE_END", Map.of("messageId", messageId)));
        events.add(event("TOOL_CALL_START", Map.of(
                "toolCallId", toolCallId,
                "toolCallName", "buildProjectionA2uiCard",
                "parentMessageId", messageId
        )));
        events.add(event("TOOL_CALL_ARGS", Map.of(
                "toolCallId", toolCallId,
                "delta", "{\"annualSalary\":100000,\"primaryContributionPercent\":6,"
                        + "\"annualSavingsAccountContribution\":4400,\"savingsAccountCoverage\":\"self-only\","
                        + "\"adjustmentRate\":24}"
        )));
        events.add(event("TOOL_CALL_END", Map.of("toolCallId", toolCallId)));
        events.add(event("STATE_SNAPSHOT", Map.of("snapshot", stateSnapshot(a2uiPayload))));
        events.add(event("RUN_FINISHED", Map.of(
                "threadId", threadId,
                "runId", runId,
                "result", Map.of(
                        "status", "projection_streamed",
                        "rung", "01D"
                )
        )));

        return events.stream()
                .map(item -> item.asProtocolMap(clock))
                .toList();
    }

    private AgUiEvent event(String type, Map<String, Object> fields) {
        return new AgUiEvent(type, fields);
    }

    private static Map<String, Object> stateSnapshot(Map<String, Object> a2uiPayload) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("phase", "rendering_projection");
        snapshot.put("rung", "01D");
        snapshot.put("status", "ready");
        snapshot.put("a2uiPayload", a2uiPayload);
        snapshot.put("safety", Map.of(
                "fictionalDataOnly", true,
                "realTransactionsAllowed", false
        ));
        return snapshot;
    }
}
