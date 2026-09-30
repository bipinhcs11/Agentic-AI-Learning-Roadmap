package com.example.engineering;

import static com.example.engineering.AgentLoop.*;
import static org.assertj.core.api.Assertions.assertThat;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;

class AgentLoopTest {
    private static final Duration BUDGET = Duration.ofSeconds(2);
    private final Gateway reads = tool -> new Evidence(tool, "fictional observation");

    @Test void successRequiresEvidenceAndBatchNeedsApproval() {
        for (Scenario scenario : Scenario.values()) {
            var result = new AgentLoop().run(scenario, 4, BUDGET, AgentLoop::nextTool, reads);
            assertThat(result.status()).isEqualTo(scenario == Scenario.BATCH ? Status.WAITING_APPROVAL : Status.COMPLETED);
            assertThat(result.evidence()).hasSize(2);
            assertThat(result.attempts()).isEqualTo(2);
        }
    }

    @Test void budgetStopsBeforeAnotherToolCall() {
        var result = new AgentLoop().run(Scenario.REST_API, 1, BUDGET, AgentLoop::nextTool, reads);
        assertThat(result.status()).isEqualTo(Status.STEP_LIMIT);
        assertThat(result.attempts()).isEqualTo(1);
    }

    @Test void repeatedActionAndFalseCompletionStop() {
        assertThat(new AgentLoop().run(Scenario.REST_API, 8, BUDGET,
            (s, e) -> Tool.READ_CONTRACT, reads).status()).isEqualTo(Status.NO_PROGRESS);
        assertThat(new AgentLoop().run(Scenario.REST_API, 8, BUDGET,
            (s, e) -> null, reads).status()).isEqualTo(Status.NO_PROGRESS);
    }

    @Test void transientReadRetriesOnceAndConsumesBudget() {
        var calls = new AtomicInteger();
        Gateway flaky = tool -> {
            if (calls.incrementAndGet() == 1) throw new TransientToolException();
            return reads.call(tool);
        };
        var result = new AgentLoop().run(Scenario.REST_API, 3, BUDGET, AgentLoop::nextTool, flaky);
        assertThat(result.status()).isEqualTo(Status.COMPLETED);
        assertThat(result.attempts()).isEqualTo(3);
        var failed = new AgentLoop().run(Scenario.REST_API, 8, BUDGET, AgentLoop::nextTool,
            tool -> { throw new TransientToolException(); });
        assertThat(failed.status()).isEqualTo(Status.TOOL_ERROR);
        assertThat(failed.attempts()).isEqualTo(2);
    }

    @Test void permanentFailureNeverRetries() {
        var result = new AgentLoop().run(Scenario.REST_API, 8, BUDGET, AgentLoop::nextTool,
            tool -> { throw new IllegalStateException("do not expose tool internals"); });
        assertThat(result.status()).isEqualTo(Status.TOOL_ERROR);
        assertThat(result.attempts()).isEqualTo(1);
        assertThat(result.recommendation()).doesNotContain("internals");
    }

    @Test void deadlineStopsAfterSlowReadAndDoesNotClaimSuccess() {
        var clock = new AtomicLong();
        var result = new AgentLoop(clock::get).run(Scenario.REST_API, 8, BUDGET, AgentLoop::nextTool,
            tool -> { clock.addAndGet(BUDGET.toNanos()); return reads.call(tool); });
        assertThat(result.status()).isEqualTo(Status.DEADLINE);
        assertThat(result.attempts()).isEqualTo(1);
    }

    @Test void mismatchedToolEvidenceIsRejected() {
        var result = new AgentLoop().run(Scenario.REST_API, 4, BUDGET, AgentLoop::nextTool,
            tool -> new Evidence(Tool.READ_CATALOG, "unrelated"));
        assertThat(result.status()).isEqualTo(Status.TOOL_ERROR);
    }
}
