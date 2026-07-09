package com.benefits.adk.ucp;

// Employee categories drive the fictional plan a new hire is eligible for.
// Category -> match tiers + savings account employer seed live in BenefitsPlanCatalog, so
// the workflow can look up "based on employee category -> primary contribution/savings account match".
public enum EmployeeCategory {
    STANDARD,
    EXECUTIVE,
    PART_TIME;

    // Accept loose labels from an LLM or a form ("part-time", "Exec", null)
    // without throwing, defaulting to the most common plan.
    public static EmployeeCategory fromLabel(String label) {
        if (label == null || label.isBlank()) {
            return STANDARD;
        }
        String normalized = label.trim().toLowerCase().replace('-', '_').replace(' ', '_');
        return switch (normalized) {
            case "executive", "exec", "leadership" -> EXECUTIVE;
            case "part_time", "parttime", "pt" -> PART_TIME;
            default -> STANDARD;
        };
    }
}
