package com.example.aiidentity.service;

import java.time.Duration;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "identity.redis.enabled", havingValue = "true")
class RedisTaskStateStore implements TaskStateStore {
    private static final String PREFIX = "phase12:task:";
    private final StringRedisTemplate redis;

    RedisTaskStateStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public void activate(String taskId, UUID agentId, Duration ttl) {
        Boolean created = redis.opsForValue().setIfAbsent(key(taskId), "ACTIVE:" + agentId, ttl);
        if (!Boolean.TRUE.equals(created)) {
            throw new IllegalStateException("Task id is already active");
        }
    }

    @Override
    public boolean isActive(String taskId, UUID agentId) {
        return ("ACTIVE:" + agentId).equals(redis.opsForValue().get(key(taskId)));
    }

    @Override
    public void revoke(String taskId, UUID agentId) {
        String key = key(taskId);
        String current = redis.opsForValue().get(key);
        if (("ACTIVE:" + agentId).equals(current)) {
            Long remainingSeconds = redis.getExpire(key);
            Duration remaining = remainingSeconds == null || remainingSeconds <= 0
                    ? Duration.ofMinutes(10)
                    : Duration.ofSeconds(remainingSeconds);
            redis.opsForValue().set(key, "REVOKED:" + agentId,
                    remaining);
        }
    }

    private static String key(String taskId) {
        return PREFIX + taskId;
    }
}
