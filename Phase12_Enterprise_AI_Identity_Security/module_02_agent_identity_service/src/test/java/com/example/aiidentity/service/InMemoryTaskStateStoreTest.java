package com.example.aiidentity.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class InMemoryTaskStateStoreTest {
    private final InMemoryTaskStateStore store = new InMemoryTaskStateStore();

    @Test
    void activatesBindsAndRevokesTask() {
        UUID agent = UUID.randomUUID();
        store.activate("task-1", agent, Duration.ofMinutes(10));
        assertThat(store.isActive("task-1", agent)).isTrue();
        assertThat(store.isActive("task-1", UUID.randomUUID())).isFalse();

        store.revoke("task-1", agent);
        assertThat(store.isActive("task-1", agent)).isFalse();
    }

    @Test
    void refusesToRebindActiveTaskIdentifier() {
        store.activate("task-1", UUID.randomUUID(), Duration.ofMinutes(10));
        assertThatThrownBy(() ->
                store.activate("task-1", UUID.randomUUID(), Duration.ofMinutes(10)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("already active");
    }
}
