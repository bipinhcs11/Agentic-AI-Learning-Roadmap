package com.benefits.adk.ui;

public record A2uiPayload(
        String schemaVersion,
        A2uiComponent root,
        A2uiValidationResult validation
) {
}
