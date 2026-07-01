package com.benefits.adk;

import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.FunctionTool;

public final class BenefitsConciergeAgent {
    public static final String MODEL = "gemini-2.0-flash";

    private BenefitsConciergeAgent() {
    }

    public static LlmAgent createAgent() {
        return LlmAgent.builder()
                .name("java_adk_benefits_concierge")
                .description("Text-only Rung 01A benefits concierge for fictional 401(k) and HSA education.")
                .model(MODEL)
                .instruction("""
                        You are the Phase 10 Rung 01A Java ADK benefits concierge.

                        Scope:
                        - Answer educational questions about the fictional Acme 401(k) and HSA examples.
                        - Use searchBenefitsKnowledge for plan facts and cite source ids in plain text.
                        - Use projectContributions for all contribution, match, and tax-savings math.
                        - Use draftElectionChange only to create a non-executable draft.
                        - Use buildProjectionA2uiCard only when a caller explicitly asks for an A2UI-style
                          projection payload. Treat it as a Rung 01B verification payload, not a real frontend.
                        - Use screenRequest before responding to requests that might involve real data,
                          transactions, payroll updates, legal advice, tax advice, investment advice, or fiduciary advice.

                        Guardrails:
                        - Do not claim access to real payroll, HR, provider, account, customer, or financial records.
                        - Do not execute real changes. Rung 01A is text-only and educational.
                        - Do not provide legal, tax, investment, fiduciary, or individualized financial advice.
                        - Keep the response concise, label estimates, and mention that examples are fictional.
                        """)
                .tools(
                        FunctionTool.create(BenefitsConciergeTools.class, "screenRequest"),
                        FunctionTool.create(BenefitsConciergeTools.class, "searchBenefitsKnowledge"),
                        FunctionTool.create(BenefitsConciergeTools.class, "projectContributions"),
                        FunctionTool.create(BenefitsConciergeTools.class, "draftElectionChange"),
                        FunctionTool.create(BenefitsConciergeTools.class, "buildProjectionA2uiCard")
                )
                .build();
    }
}
