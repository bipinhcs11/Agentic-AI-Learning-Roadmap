package com.example.engineering;

import static org.assertj.core.api.Assertions.assertThat;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

class ContractReviewTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final ContractReview review = new ContractReview(mapper);

    @Test void catchesTheDeliberateBreakingChange() {
        assertThat(review.reviewFixtures()).contains("removed required response field: name", "Block promotion");
    }

    @Test void unchangedContractDoesNotRaiseAFalseAlarm() throws Exception {
        try (var input = new ClassPathResource("fixtures/inventory-v1.json").getInputStream()) {
            var contract = mapper.readTree(input);
            assertThat(review.compare(contract, contract)).startsWith("No breaking change");
        }
    }
}
