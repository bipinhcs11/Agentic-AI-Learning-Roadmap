package com.benefits.adk.ui;

import java.util.List;

public record A2uiValidationResult(
        boolean valid,
        List<String> errors
) {
    public static A2uiValidationResult ok() {
        return new A2uiValidationResult(true, List.of());
    }

    public static A2uiValidationResult failed(List<String> errors) {
        return new A2uiValidationResult(false, List.copyOf(errors));
    }
}
