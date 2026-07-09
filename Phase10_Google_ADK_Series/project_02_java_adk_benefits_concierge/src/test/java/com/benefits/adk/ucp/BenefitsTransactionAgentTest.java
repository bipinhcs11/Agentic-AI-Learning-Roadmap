package com.benefits.adk.ucp;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.FunctionTool;
import org.junit.jupiter.api.Test;

// Verifies the ADK wiring without a live Gemini call: FunctionTool reflection
// must succeed for every transaction tool (including submitEnrollment's boolean
// parameter), and the agent must build with them registered.
class BenefitsTransactionAgentTest {

    @Test
    void functionToolsCreateForEveryTransactionTool() {
        assertNotNull(FunctionTool.create(UcpBenefitsTransactionTools.class, "previewEnrollment"));
        assertNotNull(FunctionTool.create(UcpBenefitsTransactionTools.class, "submitEnrollment"));
        assertNotNull(FunctionTool.create(UcpBenefitsTransactionTools.class, "buildPayslipA2ui"));
    }

    @Test
    void agentBuildsWithTransactionToolsRegistered() {
        LlmAgent agent = BenefitsTransactionAgent.createAgent();
        assertNotNull(agent);
    }
}
