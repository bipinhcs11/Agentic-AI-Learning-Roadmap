package com.example.securemcp;

interface TaskStatusVerifier {
    boolean isActive(String agentId, String taskId);
}
