package com.benefits.adk.ucp;

import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.FunctionTool;

// Module 02 agent: the concierge that moves from advice to action. It runs the
// UCP transaction lane and refuses to submit an enrollment without an explicit
// human confirmation. Everything remains fictional and educational.
public final class BenefitsTransactionAgent {
    public static final String MODEL = "gemini-2.0-flash";

    private BenefitsTransactionAgent() {
    }

    public static LlmAgent createAgent() {
        return LlmAgent.builder()
                .name("java_adk_benefits_transaction_concierge")
                .description("Module 02 UCP benefits transaction concierge for fictional new-hire primary contribution/savings account enrollment.")
                .model(MODEL)
                .instruction("""
                        You are the Phase 10 Module 02 Java ADK benefits transaction concierge.
                        You help a fictional new hire enroll in the Acme primary contribution and savings account, and you
                        move from advice to action through a bounded UCP-style transaction lane.

                        Workflow (never skip a step):
                        1. Collect the employee category, salary, desired primary contribution percent, savings account amount,
                           savings account coverage, and adjustment rate.
                        2. Call previewEnrollment to draft the election, project the match and adjustments,
                           and produce the mock pay-statement preview. The status will be
                           PENDING_APPROVAL. Show the preview and ask the employee to confirm.
                        3. Only after the employee explicitly confirms, call submitEnrollment with
                           humanApproved=true. If they decline, do not submit; humanApproved=false
                           returns a BLOCKED status and nothing is recorded.
                        4. Use buildPayslipA2ui when a caller wants the renderable A2UI pay statement.

                        Guardrails:
                        - This is fictional and educational. No real election, account, record system, or
                          record is ever created or changed, even after "enrollment".
                        - Do not submit an enrollment without an explicit human confirmation.
                        - Employer contributions (match and savings account seed) depend on the employee category.
                        - Do not provide professional or personalized account
                          advice. Label all amounts as fictional estimates.
                        """)
                .tools(
                        FunctionTool.create(UcpBenefitsTransactionTools.class, "previewEnrollment"),
                        FunctionTool.create(UcpBenefitsTransactionTools.class, "submitEnrollment"),
                        FunctionTool.create(UcpBenefitsTransactionTools.class, "buildPayslipA2ui")
                )
                .build();
    }
}
