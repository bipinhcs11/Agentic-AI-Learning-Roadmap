package com.benefits.adk.tools;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class ElectionDraftServiceTest {
    @Test
    void draftIsNotExecutableInRung01A() {
        ElectionDraft draft = new ElectionDraftService()
                .draft("primary_contribution-change", new BigDecimal("8"), BigDecimal.ZERO);

        assertFalse(draft.executableInRung01A());
        assertTrue(draft.approvalSteps().stream().anyMatch(step -> step.contains("Module 02 UCP")));
    }
}
