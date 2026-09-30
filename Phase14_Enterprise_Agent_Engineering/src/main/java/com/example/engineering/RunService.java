package com.example.engineering;

import static com.example.engineering.AgentLoop.*;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
class RunService {
    record Run(UUID id, String tenant, Scenario scenario, Status status, List<Evidence> evidence,
               String recommendation, int attempts, Instant createdAt, Long jobExecutionId, String reviewer) {}
    private static final Logger LOG = LoggerFactory.getLogger(RunService.class);
    private static final Duration RETENTION = Duration.ofMinutes(30);
    private final Map<UUID, Run> runs = new LinkedHashMap<>();
    private final JdbcTemplate jdbc;
    private final JobLauncher launcher;
    private final Job job;
    private final MeterRegistry metrics;
    private final ContractReview contracts;

    RunService(JdbcTemplate jdbc, JobLauncher launcher, Job catalogJob, MeterRegistry metrics, ContractReview contracts) {
        this.jdbc = jdbc; this.launcher = launcher; this.job = catalogJob; this.metrics = metrics;
        this.contracts = contracts;
    }

    synchronized Run create(String tenant, Scenario scenario, int maxSteps) {
        runs.values().removeIf(run -> expired(run));
        if (runs.size() >= 100) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Local run capacity reached");
        UUID id = UUID.randomUUID();
        long start = System.nanoTime();
        Result result = new AgentLoop().run(scenario, maxSteps, Duration.ofSeconds(2),
            AgentLoop::nextTool, tool -> readTool(tool, tenant));
        Run run = new Run(id, tenant, scenario, result.status(), result.evidence(), result.recommendation(),
            result.attempts(), Instant.now(), null, null);
        runs.put(id, run);
        metrics.counter("agent.runs", "status", run.status().name()).increment();
        metrics.timer("agent.run.duration", "scenario", scenario.name()).record(Duration.ofNanos(System.nanoTime() - start));
        LOG.info("agent_run run_id={} scenario={} status={} attempts={}", id, scenario, run.status(), run.attempts());
        return run;
    }

    private Evidence readTool(Tool tool, String tenant) {
        metrics.counter("agent.tool.calls", "tool", tool.name()).increment();
        return new Evidence(tool, switch (tool) {
            case READ_CONTRACT -> "Fixture inventory-api v1: GET /items; operationId=listItems; limit=1..100; required id/name.";
            case READ_HEALTH -> "Fixture inventory-api: available; upstream timeout=250ms, observed p95=400ms. These are synthetic observations.";
            case CHECK_COMPATIBILITY -> contracts.reviewFixtures();
            case READ_CATALOG -> "Fictional tenant catalog contains " + catalogSize(tenant) + " documents; refresh upserts two versioned fixtures.";
        });
    }

    int catalogSize(String tenant) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM demo_catalog WHERE tenant = ?", Integer.class, tenant);
    }

    synchronized Run get(UUID id, String tenant) {
        Run run = runs.get(id);
        if (run == null || !run.tenant().equals(tenant) || expired(run))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Run not found or expired");
        return run;
    }

    private boolean expired(Run run) { return run.createdAt().plus(RETENTION).isBefore(Instant.now()); }

    synchronized Run decide(UUID id, String tenant, String reviewer, boolean approved) {
        Run run = get(id, tenant);
        // Duplicate successful approval returns the original result without relaunching.
        if (approved && run.status() == Status.JOB_COMPLETED) return run;
        if (run.status() != Status.WAITING_APPROVAL)
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Run is not awaiting approval");
        Status status = Status.REJECTED;
        Long executionId = null;
        if (approved) {
            try {
                // No timestamp/random parameters: repeated calls retain the same JobInstance identity.
                var execution = launcher.run(job, new JobParametersBuilder()
                    .addString("tenant", tenant).addString("runId", id.toString()).toJobParameters());
                executionId = execution.getId();
                status = execution.getStatus() == org.springframework.batch.core.BatchStatus.COMPLETED
                    ? Status.JOB_COMPLETED : Status.JOB_FAILED;
            } catch (Exception ex) {
                status = Status.JOB_FAILED;
                LOG.warn("catalog_launch_failed run_id={} exception_type={}", id, ex.getClass().getSimpleName());
            }
        }
        Run updated = new Run(id, tenant, run.scenario(), status, run.evidence(),
            status == Status.JOB_COMPLETED ? "Two fictional documents indexed." : "No successful refresh confirmed; review decision or job status.",
            run.attempts(), run.createdAt(), executionId, reviewer);
        runs.put(id, updated);
        metrics.counter("agent.decisions", "status", status.name()).increment();
        LOG.info("agent_decision run_id={} reviewer={} status={} job_execution_id={}", id, reviewer, status, executionId);
        return updated;
    }
}
