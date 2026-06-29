package com.compliance.riskscoring.model;

import com.compliance.riskscoring.model.A2AModels.Artifact;
import com.compliance.riskscoring.model.A2AModels.Message;
import com.compliance.riskscoring.model.A2AModels.Part;
import com.compliance.riskscoring.model.A2AModels.Task;
import com.compliance.riskscoring.model.A2AModels.TaskStatus;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class A2AModelsTest {

    @Test
    void taskSerializationUsesCurrentA2AWireValues() throws Exception {
        Part dataPart = Part.dataPart(Map.of("risk_score", 21), "application/json");
        Message message = new Message(A2AModels.ROLE_AGENT, List.of(dataPart));
        message.setContextId("case-123");
        message.setMessageId("msg-case-123");
        message.setTaskId("case-123");

        Artifact artifact = new Artifact("risk_score_result", "Risk score", List.of(dataPart));
        TaskStatus status = new TaskStatus(A2AModels.TASK_STATE_COMPLETED, message, "2026-06-29T00:00:00Z");
        Task task = new Task("case-123", status, List.of(artifact));

        JsonNode json = new ObjectMapper().valueToTree(task);

        assertEquals("task", json.get("kind").asText());
        assertEquals("case-123", json.get("contextId").asText());
        assertEquals("completed", json.at("/status/state").asText());
        assertEquals("message", json.at("/status/message/kind").asText());
        assertEquals("agent", json.at("/status/message/role").asText());
        assertEquals("msg-case-123", json.at("/status/message/messageId").asText());
        assertEquals("risk_score_result", json.at("/artifacts/0/artifactId").asText());
        assertEquals("data", json.at("/artifacts/0/parts/0/kind").asText());
    }
}
