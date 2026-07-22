package com.example.securemcp;

import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
class AuditService {
    private static final Logger LOG = LoggerFactory.getLogger(AuditService.class);
    private static final int MAX_EVENTS = 200;
    private final Deque<AuditEvent> events = new ArrayDeque<>();

    synchronized void record(
            String decision,
            String tool,
            String subject,
            String tenant,
            String taskId,
            String auditId,
            String reason) {
        AuditEvent event = new AuditEvent(
                Instant.now(), decision, tool, subject, tenant, taskId, auditId, reason);
        events.addFirst(event);
        while (events.size() > MAX_EVENTS) events.removeLast();
        LOG.info(
                "security_decision={} tool={} subject={} tenant={} task={} audit_id={} reason={}",
                decision, tool, subject, tenant, taskId, auditId, reason);
    }

    synchronized List<AuditEvent> recent() {
        return new ArrayList<>(events);
    }

    record AuditEvent(
            Instant timestamp,
            String decision,
            String tool,
            String subject,
            String tenant,
            String taskId,
            String auditId,
            String reason) {}
}
