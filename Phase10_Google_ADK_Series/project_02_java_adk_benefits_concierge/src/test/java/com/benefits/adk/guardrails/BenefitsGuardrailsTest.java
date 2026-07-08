package com.benefits.adk.guardrails;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BenefitsGuardrailsTest {
    private final BenefitsGuardrails guardrails = new BenefitsGuardrails();

    @Test
    void allowsFictionalEducationRequest() {
        GuardrailDecision decision = guardrails.screenUserRequest("Explain the fictional savings account triple adjustment advantage.");

        assertTrue(decision.allowed());
        assertTrue(decision.triggeredRules().isEmpty());
    }

    @Test
    void blocksRealRecordSystemUpdate() {
        GuardrailDecision decision = guardrails.screenUserRequest("Update my record system and submit my election.");

        assertFalse(decision.allowed());
        assertTrue(decision.triggeredRules().contains("no_real_transactions_in_rung01a"));
    }

    @Test
    void keepsCommitGateClosedUntilModule02Ucp() {
        assertFalse(guardrails.isCommitAllowed(true, "rung01a"));
        assertTrue(guardrails.isCommitAllowed(true, "ucp-module02"));
    }
}
