package com.compliance.riskscoring.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

/**
 * JSON-RPC 2.0 request model.
 * Supports both standard and A2A-specific fields.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class JsonRpcRequest {

    @JsonProperty("jsonrpc")
    private String jsonrpc = "2.0";

    @JsonProperty("id")
    private Object id;

    @JsonProperty("method")
    private String method;

    @JsonProperty("params")
    private Map<String, Object> params;

    public JsonRpcRequest() {}

    // --- Getters ---

    public String getJsonrpc() {
        return jsonrpc;
    }

    public Object getId() {
        return id;
    }

    public String getMethod() {
        return method;
    }

    public Map<String, Object> getParams() {
        return params;
    }

    // --- Setters ---

    public void setJsonrpc(String jsonrpc) {
        this.jsonrpc = jsonrpc;
    }

    public void setId(Object id) {
        this.id = id;
    }

    public void setMethod(String method) {
        this.method = method;
    }

    public void setParams(Map<String, Object> params) {
        this.params = params;
    }

    @Override
    public String toString() {
        return "JsonRpcRequest{" +
                "jsonrpc='" + jsonrpc + '\'' +
                ", id=" + id +
                ", method='" + method + '\'' +
                ", params=" + params +
                '}';
    }
}
