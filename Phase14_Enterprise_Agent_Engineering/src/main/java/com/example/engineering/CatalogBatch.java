package com.example.engineering;

import java.util.List;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.configuration.annotation.StepScope;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemReader;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.support.ListItemReader;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
class CatalogBatch {
    record Document(String id, String summary) {}

    @Bean
    @StepScope
    ItemReader<Document> catalogReader() {
        // Fresh reader for each execution; fixture replay is safe through upsert writes.
        return new ListItemReader<>(List.of(
            new Document("inventory-api-v1", "Fictional inventory API: GET /items, bounded pages, read-only."),
            new Document("inventory-runbook-v1", "Fictional runbook: inspect timeout metrics before changing configuration.")));
    }

    @Bean
    @StepScope
    ItemWriter<Document> catalogWriter(JdbcTemplate jdbc, @Value("#{jobParameters['tenant']}") String tenant) {
        return chunk -> {
            for (Document doc : chunk) {
                jdbc.update("MERGE INTO demo_catalog (tenant, document_id, summary) KEY (tenant, document_id) VALUES (?, ?, ?)",
                    tenant, doc.id(), doc.summary());
            }
        };
    }

    @Bean
    Step catalogStep(JobRepository repository, PlatformTransactionManager transactions,
                     ItemReader<Document> catalogReader, ItemWriter<Document> catalogWriter) {
        return new StepBuilder("catalogStep", repository)
            .<Document, Document>chunk(2, transactions)
            .reader(catalogReader).writer(catalogWriter).build();
    }

    @Bean
    Job catalogJob(JobRepository repository, Step catalogStep) {
        return new JobBuilder("catalogRefresh", repository).start(catalogStep).build();
    }
}
