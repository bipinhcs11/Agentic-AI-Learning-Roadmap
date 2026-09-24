package com.example.engineering;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import java.util.UUID;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class ApiWorkflowTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate jdbc;

    JsonNode create(String scenario, int steps) throws Exception {
        return json.readTree(mvc.perform(post("/api/runs").with(httpBasic("reader", "reader-demo"))
            .contentType("application/json").content("{\"scenario\":\"" + scenario + "\",\"maxSteps\":" + steps + "}"))
            .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString());
    }

    @Test void readWorkflowsAndStepBudget() throws Exception {
        assertThat(create("REST_API", 4).get("status").asText()).isEqualTo("COMPLETED");
        assertThat(create("OPENAPI", 4).get("evidence").size()).isEqualTo(2);
        assertThat(create("REST_API", 1).get("status").asText()).isEqualTo("STEP_LIMIT");
    }

    @Test void approvalRunsRealBatchOnceAndUpsertsAcrossRuns() throws Exception {
        jdbc.update("DELETE FROM demo_catalog");
        var run = create("BATCH", 4);
        assertThat(run.get("status").asText()).isEqualTo("WAITING_APPROVAL");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM demo_catalog", Integer.class)).isZero();
        String path = "/api/runs/" + run.get("id").asText() + "/decision";
        mvc.perform(post(path).with(httpBasic("reader", "reader-demo"))
            .contentType("application/json").content("{\"approved\":true}"))
            .andExpect(status().isForbidden());
        JsonNode result = approve(path);
        assertThat(result.get("status").asText()).isEqualTo("JOB_COMPLETED");
        assertThat(approve(path).get("jobExecutionId")).isEqualTo(result.get("jobExecutionId"));
        var second = create("BATCH", 4);
        assertThat(approve("/api/runs/" + second.get("id").asText() + "/decision").get("status").asText()).isEqualTo("JOB_COMPLETED");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM demo_catalog WHERE tenant='demo-a'", Integer.class)).isEqualTo(2);
        mvc.perform(get("/api/catalog").with(httpBasic("other", "other-demo")))
            .andExpect(status().isOk()).andExpect(jsonPath("$.documentCount").value(0));
    }

    JsonNode approve(String path) throws Exception {
        return json.readTree(mvc.perform(post(path).with(httpBasic("reviewer", "reviewer-demo"))
            .contentType("application/json").content("{\"approved\":true}"))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    @Test void rejectionCannotBeOverridden() throws Exception {
        var run = create("BATCH", 4);
        String path = "/api/runs/" + run.get("id").asText() + "/decision";
        mvc.perform(post(path).with(httpBasic("reviewer", "reviewer-demo"))
            .contentType("application/json").content("{\"approved\":false}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"));
        mvc.perform(post(path).with(httpBasic("reviewer", "reviewer-demo"))
            .contentType("application/json").content("{\"approved\":true}"))
            .andExpect(status().isConflict());
    }

    @Test void identitiesAndUntrustedFieldsCannotBypassTheBoundary() throws Exception {
        mvc.perform(post("/api/runs").contentType("application/json")
            .content("{\"scenario\":\"BATCH\",\"maxSteps\":4}")).andExpect(status().isUnauthorized());
        var id = create("BATCH", 4).get("id").asText();
        mvc.perform(get("/api/runs/" + id).with(httpBasic("other", "other-demo")))
            .andExpect(status().isNotFound());
        for (String body : new String[] {
            "{\"scenario\":\"REST_API\",\"maxSteps\":0}",
            "{\"scenario\":\"REST_API\",\"maxSteps\":9}",
            "{\"scenario\":\"REST_API\",\"maxSteps\":1.5}",
            "{\"scenario\":\"REST_API\",\"maxSteps\":\"4\"}",
            "{\"scenario\":\"DELETE_ALL\",\"maxSteps\":4}",
            "{\"scenario\":\"BATCH\",\"maxSteps\":4,\"tenant\":\"demo-b\"}",
            "{\"scenario\":\"BATCH\",\"maxSteps\":4,\"approved\":true}"}) {
            mvc.perform(post("/api/runs").with(httpBasic("reader", "reader-demo"))
                .contentType("application/json").content(body)).andExpect(status().isBadRequest());
        }
        mvc.perform(post("/api/runs/" + UUID.randomUUID() + "/decision")
            .with(httpBasic("reviewer", "reviewer-demo")).contentType("application/json").content("{}"))
            .andExpect(status().isBadRequest());
        mvc.perform(get("/api/catalog").with(httpBasic("reader", "reader-demo"))
            .header("Origin", "https://untrusted.example")).andExpect(status().isForbidden());
    }
}
