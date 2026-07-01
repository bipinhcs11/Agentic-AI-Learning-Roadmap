package com.benefits.adk.guardrails;

import java.util.List;

public record GuardrailDecision(
        boolean allowed,
        List<String> triggeredRules,
        String responseGuidance
) {
    public static GuardrailDecision allow() {
        return new GuardrailDecision(true, List.of(), "Proceed with educational, fictional guidance.");
    }
}
