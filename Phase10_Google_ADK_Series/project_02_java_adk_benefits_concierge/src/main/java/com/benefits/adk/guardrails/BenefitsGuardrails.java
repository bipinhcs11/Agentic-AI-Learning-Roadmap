package com.benefits.adk.guardrails;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class BenefitsGuardrails {
    private static final List<String> TRANSACTION_TERMS = List.of(
            "submit election", "submit my election", "change my contribution",
            "update my record system", "move money", "execute", "confirm the trade",
            "enroll me", "open an account"
    );

    private static final List<String> REAL_DATA_TERMS = List.of(
            "my ssn", "social security", "record system id", "employee id",
            "bank account", "routing number", "customer data", "real account"
    );

    private static final List<String> ADVICE_TERMS = List.of(
            "what should i invest", "guarantee", "legal advice", "professional advice",
            "professional advice", "which fund should i buy"
    );

    public GuardrailDecision screenUserRequest(String request) {
        String normalized = request == null ? "" : request.toLowerCase(Locale.ROOT);
        List<String> triggered = new ArrayList<>();

        if (containsAny(normalized, TRANSACTION_TERMS)) {
            triggered.add("no_real_transactions_in_rung01a");
        }
        if (containsAny(normalized, REAL_DATA_TERMS)) {
            triggered.add("no_real_sensitive_or_enterprise_data");
        }
        if (containsAny(normalized, ADVICE_TERMS)) {
            triggered.add("no_personalized_legal_tax_product_advice");
        }

        if (triggered.isEmpty()) {
            return GuardrailDecision.allow();
        }

        return new GuardrailDecision(
                false,
                List.copyOf(triggered),
                "Decline the unsafe part, explain this is a fictional educational demo, "
                        + "and offer a safe example calculation or high-level explanation instead."
        );
    }

    public boolean isCommitAllowed(boolean explicitHumanConfirmation, String transactionLane) {
        return explicitHumanConfirmation && "ucp-module02".equals(transactionLane);
    }

    private static boolean containsAny(String text, List<String> terms) {
        return terms.stream().anyMatch(text::contains);
    }
}
