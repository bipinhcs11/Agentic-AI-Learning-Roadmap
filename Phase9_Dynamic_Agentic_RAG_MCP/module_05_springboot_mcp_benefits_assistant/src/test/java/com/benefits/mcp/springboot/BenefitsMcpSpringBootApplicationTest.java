package com.benefits.mcp.springboot;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "server.port=0")
class BenefitsMcpSpringBootApplicationTest {

    @Test
    void contextLoads() {
    }
}
