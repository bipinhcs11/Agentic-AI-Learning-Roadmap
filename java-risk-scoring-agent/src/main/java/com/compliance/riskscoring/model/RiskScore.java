package com.compliance.riskscoring.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * POJO representing the risk scoring output returned by the agent.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RiskScore {

    @JsonProperty("risk_score")
    private int riskScore;

    @JsonProperty("risk_grade")
    private String riskGrade;

    @JsonProperty("risk_breakdown")
    private Map<String, Object> riskBreakdown;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("scoring_timestamp")
    private String scoringTimestamp;

    @JsonProperty("contractor_name")
    private String contractorName;

    @JsonProperty("client_name")
    private String clientName;

    @JsonProperty("contract_value")
    private double contractValue;

    public RiskScore() {}

    // --- Getters ---

    public int getRiskScore() {
        return riskScore;
    }

    public String getRiskGrade() {
        return riskGrade;
    }

    public Map<String, Object> getRiskBreakdown() {
        return riskBreakdown;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public String getScoringTimestamp() {
        return scoringTimestamp;
    }

    public String getContractorName() {
        return contractorName;
    }

    public String getClientName() {
        return clientName;
    }

    public double getContractValue() {
        return contractValue;
    }

    // --- Setters ---

    public void setRiskScore(int riskScore) {
        this.riskScore = riskScore;
    }

    public void setRiskGrade(String riskGrade) {
        this.riskGrade = riskGrade;
    }

    public void setRiskBreakdown(Map<String, Object> riskBreakdown) {
        this.riskBreakdown = riskBreakdown;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

    public void setScoringTimestamp(String scoringTimestamp) {
        this.scoringTimestamp = scoringTimestamp;
    }

    public void setContractorName(String contractorName) {
        this.contractorName = contractorName;
    }

    public void setClientName(String clientName) {
        this.clientName = clientName;
    }

    public void setContractValue(double contractValue) {
        this.contractValue = contractValue;
    }

    @Override
    public String toString() {
        return "RiskScore{" +
                "riskScore=" + riskScore +
                ", riskGrade='" + riskGrade + '\'' +
                ", riskBreakdown=" + riskBreakdown +
                ", recommendations=" + recommendations +
                ", scoringTimestamp='" + scoringTimestamp + '\'' +
                '}';
    }
}
