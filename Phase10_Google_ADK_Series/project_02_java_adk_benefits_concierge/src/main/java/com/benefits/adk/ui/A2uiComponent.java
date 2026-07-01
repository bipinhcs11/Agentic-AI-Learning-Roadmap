package com.benefits.adk.ui;

import java.util.List;
import java.util.Map;

public record A2uiComponent(
        String type,
        Map<String, Object> props,
        List<A2uiComponent> children
) {
    public A2uiComponent {
        props = props == null ? Map.of() : Map.copyOf(props);
        children = children == null ? List.of() : List.copyOf(children);
    }
}
