package com.compliance.riskscoring.handler;

import com.compliance.riskscoring.model.*;
import com.compliance.riskscoring.model.A2AModels.*;
import com.compliance.riskscoring.scoring.RiskCalculator;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * JSON-RPC 2.0 handler for A2A protocol messages.
 *
 * Supported methods:
 *   - message/send, SendMessage  (current A2A)
 *   - tasks/send                 (legacy A2A)
 *   - tasks/get, GetTask         (task retrieval)
 *
 * Extracts contract data from DataParts in A2A messages, runs the
 * RiskCalculator, and returns a completed Task with the risk score.
 */
public class JsonRpcHandler implements HttpHandler {

    private final ObjectMapper mapper;
    private final RiskCalculator riskCalculator;
    private final ConcurrentHashMap<String, Task> taskStore;

    public JsonRpcHandler(ObjectMapper mapper) {
        this.mapper = mapper;
        this.riskCalculator = new RiskCalculator();
        this.taskStore = new ConcurrentHashMap<>();
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        // CORS headers on every response
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type, Authorization");

        if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
            exchange.sendResponseHeaders(204, -1);
            return;
        }

        if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(exchange, 405,
                    JsonRpcResponse.error(null, JsonRpcResponse.INVALID_REQUEST, "Only POST is accepted"));
            return;
        }

        // Read the request body
        byte[] body;
        try (InputStream is = exchange.getRequestBody()) {
            body = is.readAllBytes();
        }

        if (body.length == 0) {
            sendJson(exchange, 400,
                    JsonRpcResponse.error(null, JsonRpcResponse.PARSE_ERROR, "Empty request body"));
            return;
        }

        // Parse JSON-RPC request
        JsonRpcRequest request;
        try {
            request = mapper.readValue(body, JsonRpcRequest.class);
        } catch (Exception e) {
            System.err.println("[ERROR] Failed to parse JSON-RPC request: " + e.getMessage());
            sendJson(exchange, 400,
                    JsonRpcResponse.error(null, JsonRpcResponse.PARSE_ERROR,
                            "Invalid JSON: " + e.getMessage()));
            return;
        }

        String method = request.getMethod();
        if (method == null || method.isBlank()) {
            sendJson(exchange, 400,
                    JsonRpcResponse.error(request.getId(), JsonRpcResponse.INVALID_REQUEST,
                            "Missing 'method' field"));
            return;
        }

        System.out.printf("[INFO] JSON-RPC method=%s id=%s%n", method, request.getId());

        // Route to the appropriate handler
        JsonRpcResponse response = switch (method) {
            case "message/send", "SendMessage", "tasks/send" ->
                    handleMessageSend(request);
            case "tasks/get", "GetTask" ->
                    handleTasksGet(request);
            default ->
                    JsonRpcResponse.error(request.getId(), JsonRpcResponse.METHOD_NOT_FOUND,
                            "Unknown method: " + method);
        };

        sendJson(exchange, 200, response);
    }

    /**
     * Handles message/send, SendMessage, and tasks/send methods.
     * Extracts contract data, computes risk score, returns completed Task.
     */
    private JsonRpcResponse handleMessageSend(JsonRpcRequest request) {
        Map<String, Object> params = request.getParams();
        if (params == null) {
            return JsonRpcResponse.error(request.getId(), JsonRpcResponse.INVALID_PARAMS,
                    "Missing 'params' in request");
        }

        // Extract the message from params
        Map<String, Object> messageMap = extractMap(params, "message");
        if (messageMap == null) {
            // Maybe params itself contains the message fields (legacy format)
            messageMap = params;
        }

        // Resolve task ID from multiple possible sources
        String taskId = resolveTaskId(params, messageMap);

        // Extract contract data from message parts
        ContractDetails contract = extractContractFromMessage(messageMap, params);

        if (contract == null) {
            // Try extracting directly from params as a fallback
            contract = extractContractFromMap(params);
        }

        if (contract == null) {
            Task errorTask = buildErrorTask(taskId, "No contract data found in the message. " +
                    "Expected contract fields in a DataPart or as direct fields in params.");
            taskStore.put(errorTask.getId(), errorTask);
            return JsonRpcResponse.success(request.getId(), errorTask);
        }

        System.out.printf("[INFO] Scoring contract: contractor=%s, value=$%,.0f, taskId=%s%n",
                contract.getContractorName(), contract.getContractValue(), taskId);

        // Compute risk score
        RiskScore riskScore;
        try {
            riskScore = riskCalculator.calculate(contract);
        } catch (Exception e) {
            System.err.println("[ERROR] Risk calculation failed: " + e.getMessage());
            Task errorTask = buildErrorTask(taskId, "Risk calculation error: " + e.getMessage());
            taskStore.put(errorTask.getId(), errorTask);
            return JsonRpcResponse.success(request.getId(), errorTask);
        }

        System.out.printf("[INFO] Risk score computed: score=%d, grade=%s%n",
                riskScore.getRiskScore(), riskScore.getRiskGrade());

        // Build the completed task
        Task task = buildCompletedTask(taskId, riskScore);
        taskStore.put(task.getId(), task);

        return JsonRpcResponse.success(request.getId(), task);
    }

    /**
     * Handles tasks/get and GetTask methods.
     * Retrieves a previously completed task by ID.
     */
    private JsonRpcResponse handleTasksGet(JsonRpcRequest request) {
        Map<String, Object> params = request.getParams();
        if (params == null) {
            return JsonRpcResponse.error(request.getId(), JsonRpcResponse.INVALID_PARAMS,
                    "Missing 'params'");
        }

        String taskId = extractString(params, "id");
        if (taskId == null) {
            taskId = extractString(params, "taskId");
        }
        if (taskId == null) {
            return JsonRpcResponse.error(request.getId(), JsonRpcResponse.INVALID_PARAMS,
                    "Missing task 'id' in params");
        }

        Task task = taskStore.get(taskId);
        if (task == null) {
            return JsonRpcResponse.error(request.getId(), -32001,
                    "Task not found: " + taskId);
        }

        return JsonRpcResponse.success(request.getId(), task);
    }

    // ==================== Contract Extraction ====================

    /**
     * Extracts contract details from message parts.
     * Searches through all parts for a DataPart containing contract fields.
     * Supports nested "contract" and "contract_details" keys.
     */
    @SuppressWarnings("unchecked")
    private ContractDetails extractContractFromMessage(Map<String, Object> messageMap,
                                                       Map<String, Object> outerParams) {
        // Look for parts in the message
        List<Map<String, Object>> parts = extractList(messageMap, "parts");
        if (parts == null) {
            return null;
        }

        for (Map<String, Object> partMap : parts) {
            String kind = extractString(partMap, "kind");
            if (kind == null) {
                kind = extractString(partMap, "type");
            }

            if ("data".equals(kind) && partMap.containsKey("data")) {
                Object dataObj = partMap.get("data");
                if (dataObj instanceof Map) {
                    Map<String, Object> data = (Map<String, Object>) dataObj;
                    ContractDetails contract = extractContractFromDataMap(data);
                    if (contract != null) {
                        return contract;
                    }
                }
            }
        }

        return null;
    }

    /**
     * Extracts contract from a data map, checking nested keys.
     * Supports: direct fields, "contract" nested key, "contract_details" nested key.
     */
    @SuppressWarnings("unchecked")
    private ContractDetails extractContractFromDataMap(Map<String, Object> data) {
        // Check for nested "contract" key
        if (data.containsKey("contract") && data.get("contract") instanceof Map) {
            ContractDetails contract = extractContractFromMap(
                    (Map<String, Object>) data.get("contract"));
            if (contract != null) return contract;
        }

        // Check for nested "contract_details" key
        if (data.containsKey("contract_details") && data.get("contract_details") instanceof Map) {
            ContractDetails contract = extractContractFromMap(
                    (Map<String, Object>) data.get("contract_details"));
            if (contract != null) return contract;
        }

        // Try direct fields
        return extractContractFromMap(data);
    }

    /**
     * Converts a map of fields into a ContractDetails object.
     * Returns null if the map doesn't contain recognizable contract fields.
     */
    private ContractDetails extractContractFromMap(Map<String, Object> data) {
        if (data == null || data.isEmpty()) return null;

        // Check if this looks like contract data (must have at least contract_value or contractor_name)
        if (!data.containsKey("contract_value") && !data.containsKey("contractor_name")) {
            return null;
        }

        try {
            // Use Jackson to convert the map, which handles type coercion
            return mapper.convertValue(data, ContractDetails.class);
        } catch (Exception e) {
            System.err.println("[WARN] Failed to deserialize contract data: " + e.getMessage());
            return null;
        }
    }

    // ==================== Task ID Resolution ====================

    /**
     * Resolves the task ID from multiple possible sources:
     * 1. message.taskId
     * 2. params.metadata.task_id
     * 3. params.data.case_id (envelope)
     * 4. params.id
     * 5. Auto-generated UUID
     */
    @SuppressWarnings("unchecked")
    private String resolveTaskId(Map<String, Object> params, Map<String, Object> messageMap) {
        // 1. From message taskId
        String taskId = extractString(messageMap, "taskId");
        if (taskId != null) return taskId;

        // 2. From params metadata
        Map<String, Object> metadata = extractMap(params, "metadata");
        if (metadata != null) {
            taskId = extractString(metadata, "task_id");
            if (taskId != null) return taskId;
        }

        // Also check message metadata
        metadata = extractMap(messageMap, "metadata");
        if (metadata != null) {
            taskId = extractString(metadata, "task_id");
            if (taskId != null) return taskId;
        }

        // 3. From nested data parts - look for case_id
        List<Map<String, Object>> parts = extractList(messageMap, "parts");
        if (parts != null) {
            for (Map<String, Object> part : parts) {
                Object dataObj = part.get("data");
                if (dataObj instanceof Map) {
                    Map<String, Object> data = (Map<String, Object>) dataObj;
                    String caseId = extractString(data, "case_id");
                    if (caseId != null) return caseId;
                }
            }
        }

        // 4. From params.id
        taskId = extractString(params, "id");
        if (taskId != null) return taskId;

        // 5. Auto-generate
        return UUID.randomUUID().toString();
    }

    // ==================== Task Building ====================

    /**
     * Builds a completed task with the risk score result.
     */
    private Task buildCompletedTask(String taskId, RiskScore riskScore) {
        String now = DateTimeFormatter.ISO_INSTANT.format(Instant.now());

        // Convert risk score to a map for the DataPart
        @SuppressWarnings("unchecked")
        Map<String, Object> resultData = mapper.convertValue(riskScore,
                new TypeReference<Map<String, Object>>() {});

        Part dataPart = Part.dataPart(resultData, "application/json");

        Message agentMessage = new Message(A2AModels.ROLE_AGENT, List.of(dataPart));

        Artifact artifact = new Artifact(
                "risk_score_result",
                "Quantitative financial risk score and analysis",
                List.of(dataPart));
        artifact.setIndex(0);

        TaskStatus status = new TaskStatus(
                A2AModels.TASK_STATE_COMPLETED,
                agentMessage,
                now);

        Task task = new Task(taskId, status, List.of(artifact));
        task.setHistory(List.of(agentMessage));

        return task;
    }

    /**
     * Builds a failed task for error cases.
     */
    private Task buildErrorTask(String taskId, String errorMessage) {
        if (taskId == null || taskId.isBlank()) {
            taskId = UUID.randomUUID().toString();
        }

        String now = DateTimeFormatter.ISO_INSTANT.format(Instant.now());

        Part textPart = Part.textPart(errorMessage);
        Message agentMessage = new Message(A2AModels.ROLE_AGENT, List.of(textPart));

        TaskStatus status = new TaskStatus(
                A2AModels.TASK_STATE_FAILED,
                agentMessage,
                now);

        return new Task(taskId, status, null);
    }

    // ==================== Utility Methods ====================

    /**
     * Sends a JSON response with the given HTTP status code.
     */
    private void sendJson(HttpExchange exchange, int statusCode, Object responseBody)
            throws IOException {
        byte[] responseBytes = mapper.writeValueAsBytes(responseBody);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(statusCode, responseBytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(responseBytes);
        }
    }

    /**
     * Safely extracts a string value from a map.
     */
    private String extractString(Map<String, Object> map, String key) {
        if (map == null) return null;
        Object val = map.get(key);
        return (val instanceof String s) ? s : null;
    }

    /**
     * Safely extracts a nested map from a map.
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> extractMap(Map<String, Object> map, String key) {
        if (map == null) return null;
        Object val = map.get(key);
        return (val instanceof Map) ? (Map<String, Object>) val : null;
    }

    /**
     * Safely extracts a list of maps from a map.
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> extractList(Map<String, Object> map, String key) {
        if (map == null) return null;
        Object val = map.get(key);
        return (val instanceof List) ? (List<Map<String, Object>>) val : null;
    }
}
