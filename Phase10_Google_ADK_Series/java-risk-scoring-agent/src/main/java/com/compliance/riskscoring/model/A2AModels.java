package com.compliance.riskscoring.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * A2A (Agent-to-Agent) protocol models.
 * Mirrors the structure used by the Go compliance agent for interoperability.
 */
public final class A2AModels {

    private A2AModels() {} // Prevent instantiation

    // --- Constants ---
    // Current A2A wire values used by the Python a2a-sdk/ADK RemoteA2aAgent.
    public static final String TASK_STATE_COMPLETED = "completed";
    public static final String TASK_STATE_FAILED = "failed";
    public static final String TASK_STATE_WORKING = "working";
    public static final String TASK_STATE_SUBMITTED = "submitted";

    public static final String ROLE_AGENT = "agent";
    public static final String ROLE_USER = "user";

    public static final String PART_KIND_DATA = "data";
    public static final String PART_KIND_TEXT = "text";

    // --- Task ---

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Task {

        @JsonProperty("id")
        private String id;

        @JsonProperty("contextId")
        private String contextId;

        @JsonProperty("kind")
        private String kind = "task";

        @JsonProperty("status")
        private TaskStatus status;

        @JsonProperty("artifacts")
        private List<Artifact> artifacts;

        @JsonProperty("history")
        private List<Message> history;

        @JsonProperty("metadata")
        private Map<String, Object> metadata;

        public Task() {}

        public Task(String id, TaskStatus status, List<Artifact> artifacts) {
            this.id = id;
            this.contextId = id;
            this.kind = "task";
            this.status = status;
            this.artifacts = artifacts;
        }

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getContextId() { return contextId; }
        public void setContextId(String contextId) { this.contextId = contextId; }

        public String getKind() { return kind; }
        public void setKind(String kind) { this.kind = kind; }

        public TaskStatus getStatus() { return status; }
        public void setStatus(TaskStatus status) { this.status = status; }

        public List<Artifact> getArtifacts() { return artifacts; }
        public void setArtifacts(List<Artifact> artifacts) { this.artifacts = artifacts; }

        public List<Message> getHistory() { return history; }
        public void setHistory(List<Message> history) { this.history = history; }

        public Map<String, Object> getMetadata() { return metadata; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    }

    // --- TaskStatus ---

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class TaskStatus {

        @JsonProperty("state")
        private String state;

        @JsonProperty("message")
        private Message message;

        @JsonProperty("timestamp")
        private String timestamp;

        public TaskStatus() {}

        public TaskStatus(String state, Message message) {
            this.state = state;
            this.message = message;
        }

        public TaskStatus(String state, Message message, String timestamp) {
            this.state = state;
            this.message = message;
            this.timestamp = timestamp;
        }

        public String getState() { return state; }
        public void setState(String state) { this.state = state; }

        public Message getMessage() { return message; }
        public void setMessage(Message message) { this.message = message; }

        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
    }

    // --- Message ---

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Message {

        @JsonProperty("role")
        private String role;

        @JsonProperty("kind")
        private String kind = "message";

        @JsonProperty("messageId")
        private String messageId;

        @JsonProperty("contextId")
        private String contextId;

        @JsonProperty("parts")
        private List<Part> parts;

        @JsonProperty("taskId")
        private String taskId;

        @JsonProperty("metadata")
        private Map<String, Object> metadata;

        public Message() {}

        public Message(String role, List<Part> parts) {
            this.role = role;
            this.kind = "message";
            this.parts = parts;
        }

        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }

        public String getKind() { return kind; }
        public void setKind(String kind) { this.kind = kind; }

        public String getMessageId() { return messageId; }
        public void setMessageId(String messageId) { this.messageId = messageId; }

        public String getContextId() { return contextId; }
        public void setContextId(String contextId) { this.contextId = contextId; }

        public List<Part> getParts() { return parts; }
        public void setParts(List<Part> parts) { this.parts = parts; }

        public String getTaskId() { return taskId; }
        public void setTaskId(String taskId) { this.taskId = taskId; }

        public Map<String, Object> getMetadata() { return metadata; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    }

    // --- Part ---

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Part {

        /** Current A2A uses "kind", legacy uses "type" */
        @JsonProperty("kind")
        private String kind;

        @JsonProperty("type")
        private String type;

        /** For text parts */
        @JsonProperty("text")
        private String text;

        /** For data parts - the actual data payload */
        @JsonProperty("data")
        private Object data;

        /** For data parts - MIME type of the data */
        @JsonProperty("mediaType")
        private String mediaType;

        @JsonProperty("metadata")
        private Map<String, Object> metadata;

        public Part() {}

        /**
         * Creates a DataPart with the given data payload and media type.
         */
        public static Part dataPart(Object data, String mediaType) {
            Part p = new Part();
            p.setKind(PART_KIND_DATA);
            p.setType(PART_KIND_DATA); // backward compat
            p.setData(data);
            p.setMediaType(mediaType);
            return p;
        }

        /**
         * Creates a TextPart with the given text.
         */
        public static Part textPart(String text) {
            Part p = new Part();
            p.setKind(PART_KIND_TEXT);
            p.setType(PART_KIND_TEXT); // backward compat
            p.setText(text);
            return p;
        }

        /**
         * Returns the effective kind, checking both "kind" and "type" fields.
         */
        public String getEffectiveKind() {
            if (kind != null && !kind.isBlank()) {
                return kind;
            }
            return type;
        }

        /**
         * Returns true if this is a data part.
         */
        public boolean isDataPart() {
            String k = getEffectiveKind();
            return PART_KIND_DATA.equals(k);
        }

        /**
         * Returns true if this is a text part.
         */
        public boolean isTextPart() {
            String k = getEffectiveKind();
            return PART_KIND_TEXT.equals(k);
        }

        // --- Getters / Setters ---

        public String getKind() { return kind; }
        public void setKind(String kind) { this.kind = kind; }

        public String getType() { return type; }
        public void setType(String type) { this.type = type; }

        public String getText() { return text; }
        public void setText(String text) { this.text = text; }

        public Object getData() { return data; }
        public void setData(Object data) { this.data = data; }

        public String getMediaType() { return mediaType; }
        public void setMediaType(String mediaType) { this.mediaType = mediaType; }

        public Map<String, Object> getMetadata() { return metadata; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    }

    // --- Artifact ---

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Artifact {

        @JsonProperty("name")
        private String name;

        @JsonProperty("artifactId")
        private String artifactId;

        @JsonProperty("description")
        private String description;

        @JsonProperty("parts")
        private List<Part> parts;

        @JsonProperty("index")
        private Integer index;

        @JsonProperty("metadata")
        private Map<String, Object> metadata;

        public Artifact() {}

        public Artifact(String name, String description, List<Part> parts) {
            this.name = name;
            this.artifactId = name;
            this.description = description;
            this.parts = parts;
        }

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getArtifactId() { return artifactId; }
        public void setArtifactId(String artifactId) { this.artifactId = artifactId; }

        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }

        public List<Part> getParts() { return parts; }
        public void setParts(List<Part> parts) { this.parts = parts; }

        public Integer getIndex() { return index; }
        public void setIndex(Integer index) { this.index = index; }

        public Map<String, Object> getMetadata() { return metadata; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    }
}
