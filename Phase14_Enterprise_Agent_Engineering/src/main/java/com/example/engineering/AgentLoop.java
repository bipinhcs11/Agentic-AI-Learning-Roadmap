package com.example.engineering;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.LongSupplier;

/** Application-owned control loop. Planner output never grants permission. */
public class AgentLoop {
    public enum Scenario { REST_API, OPENAPI, BATCH }
    public enum Tool { READ_CONTRACT, READ_HEALTH, CHECK_COMPATIBILITY, READ_CATALOG }
    public enum Status { COMPLETED, WAITING_APPROVAL, STEP_LIMIT, DEADLINE, NO_PROGRESS, TOOL_ERROR, REJECTED, JOB_COMPLETED, JOB_FAILED }
    public record Evidence(Tool tool, String summary) {}
    public record Result(Status status, List<Evidence> evidence, String recommendation, int attempts) {}
    @FunctionalInterface public interface Planner {
        Tool next(Scenario scenario, List<Evidence> evidence);
    }
    @FunctionalInterface public interface Gateway {
        Evidence call(Tool tool);
    }
    /** Only transient, read-only tool failures are eligible for a retry. */
    public static class TransientToolException extends RuntimeException {}

    public static Tool nextTool(Scenario scenario, List<Evidence> evidence) {
        if (evidence.isEmpty()) return Tool.READ_CONTRACT;
        if (evidence.size() == 1) return requiredTool(scenario);
        return null;
    }

    private static Tool requiredTool(Scenario scenario) {
        return switch (scenario) {
            case BATCH -> Tool.READ_CATALOG;
            case OPENAPI -> Tool.CHECK_COMPATIBILITY;
            case REST_API -> Tool.READ_HEALTH;
        };
    }

    private final LongSupplier nanoTime;
    public AgentLoop() { this(System::nanoTime); }
    AgentLoop(LongSupplier nanoTime) { this.nanoTime = nanoTime; }

    public Result run(Scenario scenario, int maxSteps, Duration deadline, Planner planner, Gateway gateway) {
        if (maxSteps < 1 || maxSteps > 8 || deadline.isNegative() || deadline.isZero()) {
            throw new IllegalArgumentException("Invalid loop budget");
        }
        long start = nanoTime.getAsLong();
        var evidence = new ArrayList<Evidence>();
        Set<Tool> completed = new HashSet<>();
        int attempts = 0;
        while (true) {
            if (nanoTime.getAsLong() - start >= deadline.toNanos())
                return result(Status.DEADLINE, evidence, attempts);
            Tool tool = planner.next(scenario, List.copyOf(evidence));
            if (nanoTime.getAsLong() - start >= deadline.toNanos())
                return result(Status.DEADLINE, evidence, attempts);
            if (tool == null) {
                // Validate goal evidence independently of the planner's claim of success.
                Tool required = requiredTool(scenario);
                if (!completed.containsAll(Set.of(Tool.READ_CONTRACT, required)))
                    return result(Status.NO_PROGRESS, evidence, attempts);
                return result(scenario == Scenario.BATCH ? Status.WAITING_APPROVAL : Status.COMPLETED, evidence, attempts);
            }
            if (attempts >= maxSteps) return result(Status.STEP_LIMIT, evidence, attempts);
            if (completed.contains(tool)) return result(Status.NO_PROGRESS, evidence, attempts);
            boolean success = false;
            for (int retry = 0; retry < 2; retry++) {
                if (attempts >= maxSteps) return result(Status.STEP_LIMIT, evidence, attempts);
                if (nanoTime.getAsLong() - start >= deadline.toNanos()) return result(Status.DEADLINE, evidence, attempts);
                attempts++;
                try {
                    Evidence observed = gateway.call(tool);
                    if (observed == null || observed.tool() != tool || observed.summary() == null)
                        return result(Status.TOOL_ERROR, evidence, attempts);
                    evidence.add(observed);
                    completed.add(tool);
                    success = true;
                    break;
                } catch (TransientToolException ex) {
                    // At most one retry, charged to the same global budget.
                } catch (RuntimeException ex) {
                    return result(Status.TOOL_ERROR, evidence, attempts);
                }
            }
            if (!success) return result(Status.TOOL_ERROR, evidence, attempts);
        }
    }

    private Result result(Status status, List<Evidence> evidence, int attempts) {
        String recommendation = switch (status) {
            case COMPLETED -> "Review fictional inventory-api timeout settings and contract compatibility before changing code.";
            case WAITING_APPROVAL -> "Refresh the two fictional catalog documents; reviewer approval is required.";
            default -> "Stopped without a write. Review the available evidence and stop reason.";
        };
        return new Result(status, List.copyOf(evidence), recommendation, attempts);
    }
}
