package com.benefits.mcp.springboot;

import java.util.List;

import org.springaicommunity.mcp.annotation.McpArg;
import org.springaicommunity.mcp.annotation.McpPrompt;
import org.springframework.stereotype.Component;

import io.modelcontextprotocol.spec.McpSchema.GetPromptResult;
import io.modelcontextprotocol.spec.McpSchema.PromptMessage;
import io.modelcontextprotocol.spec.McpSchema.Role;
import io.modelcontextprotocol.spec.McpSchema.TextContent;

@Component
public class BenefitsMcpPrompts {

    @McpPrompt(
            name = "benefits_question_prompt",
            description = "Safe prompt template for answering mock 401(k)/HSA questions with tools and RAG.")
    public GetPromptResult benefitsQuestionPrompt(
            @McpArg(name = "question", description = "The user's benefits question.", required = true)
            String question) {
        String prompt = """
                You are an educational benefits assistant.

                Use MCP tools for fictional employee/account data.
                Use search_benefits_docs for 401(k)/HSA rules, limits, eligibility, and citations.
                Cite source document filenames when retrieved context is used.

                Safety boundary: educational only; not financial, tax, legal, or investment advice.

                User question: %s
                """.formatted(question);
        return new GetPromptResult(
                "Safe benefits question prompt",
                List.of(new PromptMessage(Role.USER, new TextContent(prompt))));
    }
}
