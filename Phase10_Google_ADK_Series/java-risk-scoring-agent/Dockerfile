# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# --- Stage 1: Build with Maven ---
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /build

COPY pom.xml .
# Download dependencies first (layer caching optimization)
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn package -DskipTests -B

# --- Stage 2: Minimal JRE Runtime ---
FROM eclipse-temurin:17-jre-alpine

LABEL maintainer="Compliance Pipeline"
LABEL description="Java-based Financial Risk Scoring Engine (A2A Protocol)"

WORKDIR /app

# Copy the uber jar from the build stage
COPY --from=builder /build/target/risk-scoring-agent-1.0.0.jar /app/risk-scoring-agent.jar

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=9999
ENV AGENT_URL=http://localhost:9999

EXPOSE 9999

# Health check using the agent card endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:9999/.well-known/agent.json || exit 1

ENTRYPOINT ["java", "-jar", "/app/risk-scoring-agent.jar"]
