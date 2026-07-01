package com.benefits.adk.ui;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class TrustedA2uiCatalog {
    private static final Set<String> ALLOWED_COMPONENTS = Set.of("Card", "Text", "Table");
    private static final Set<String> BLOCKED_PROP_NAMES = Set.of("html", "script", "srcdoc", "onClick", "onLoad", "href");

    public A2uiValidationResult validate(A2uiComponent component) {
        List<String> errors = new ArrayList<>();
        validateComponent(component, "root", errors);
        return errors.isEmpty() ? A2uiValidationResult.ok() : A2uiValidationResult.failed(errors);
    }

    private static void validateComponent(A2uiComponent component, String path, List<String> errors) {
        if (component == null) {
            errors.add(path + " is missing");
            return;
        }
        if (!ALLOWED_COMPONENTS.contains(component.type())) {
            errors.add(path + " uses untrusted component type: " + component.type());
        }
        validateProps(component.props(), path, errors);
        for (int index = 0; index < component.children().size(); index++) {
            validateComponent(component.children().get(index), path + ".children[" + index + "]", errors);
        }
    }

    private static void validateProps(Map<String, Object> props, String path, List<String> errors) {
        for (String key : props.keySet()) {
            if (BLOCKED_PROP_NAMES.contains(key) || key.toLowerCase(Locale.ROOT).startsWith("on")) {
                errors.add(path + " contains blocked prop: " + key);
            }
        }
    }
}
