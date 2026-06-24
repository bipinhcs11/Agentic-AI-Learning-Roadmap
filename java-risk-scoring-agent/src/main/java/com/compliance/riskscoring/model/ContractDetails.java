package com.compliance.riskscoring.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * POJO representing contract input data extracted by the Python extractor.
 * Supports flexible field naming and type coercion for robust deserialization.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ContractDetails {

    @JsonProperty("contract_value")
    private double contractValue;

    @JsonProperty("contractor_name")
    private String contractorName;

    @JsonProperty("client_name")
    private String clientName;

    @JsonProperty("start_date")
    private String startDate;

    @JsonProperty("end_date")
    private String endDate;

    @JsonProperty("liability_limit")
    private String liabilityLimit;

    @JsonProperty("insurance_coverage")
    private double insuranceCoverage;

    @JsonProperty("auto_renewal")
    private boolean autoRenewal;

    @JsonProperty("has_termination_clause")
    private boolean hasTerminationClause;

    @JsonProperty("term_length_years")
    private double termLengthYears;

    public ContractDetails() {}

    // --- Getters ---

    public double getContractValue() {
        return contractValue;
    }

    public String getContractorName() {
        return contractorName;
    }

    public String getClientName() {
        return clientName;
    }

    public String getStartDate() {
        return startDate;
    }

    public String getEndDate() {
        return endDate;
    }

    public String getLiabilityLimit() {
        return liabilityLimit;
    }

    public double getInsuranceCoverage() {
        return insuranceCoverage;
    }

    public boolean isAutoRenewal() {
        return autoRenewal;
    }

    public boolean isHasTerminationClause() {
        return hasTerminationClause;
    }

    public double getTermLengthYears() {
        return termLengthYears;
    }

    // --- Setters ---

    public void setContractValue(double contractValue) {
        this.contractValue = contractValue;
    }

    public void setContractorName(String contractorName) {
        this.contractorName = contractorName;
    }

    public void setClientName(String clientName) {
        this.clientName = clientName;
    }

    public void setStartDate(String startDate) {
        this.startDate = startDate;
    }

    public void setEndDate(String endDate) {
        this.endDate = endDate;
    }

    public void setLiabilityLimit(String liabilityLimit) {
        this.liabilityLimit = liabilityLimit;
    }

    public void setInsuranceCoverage(double insuranceCoverage) {
        this.insuranceCoverage = insuranceCoverage;
    }

    public void setAutoRenewal(boolean autoRenewal) {
        this.autoRenewal = autoRenewal;
    }

    public void setHasTerminationClause(boolean hasTerminationClause) {
        this.hasTerminationClause = hasTerminationClause;
    }

    public void setTermLengthYears(double termLengthYears) {
        this.termLengthYears = termLengthYears;
    }

    /**
     * Checks whether the liability is unlimited (no cap specified).
     * Treats null, empty, "unlimited", "unlimited liability", "waived",
     * "inapplicable", "none", and "n/a" as unlimited — matching the Go
     * agent's prohibited clause detection patterns.
     */
    public boolean isLiabilityUnlimited() {
        if (liabilityLimit == null || liabilityLimit.isBlank()) {
            return true;
        }
        String normalized = liabilityLimit.trim().toLowerCase();
        return normalized.contains("unlimited") ||
               normalized.contains("waived") ||
               normalized.contains("inapplicable") ||
               normalized.equals("none") ||
               normalized.equals("n/a");
    }

    /**
     * Parses the liability limit string into a numeric dollar value.
     * Strips currency symbols, commas, and whitespace.
     * Returns 0 if the value cannot be parsed or is unlimited.
     */
    public double getParsedLiabilityLimit() {
        if (isLiabilityUnlimited()) {
            return 0.0;
        }
        try {
            String cleaned = liabilityLimit
                    .replaceAll("[^\\d.]", "");
            return Double.parseDouble(cleaned);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    @Override
    public String toString() {
        return "ContractDetails{" +
                "contractValue=" + contractValue +
                ", contractorName='" + contractorName + '\'' +
                ", clientName='" + clientName + '\'' +
                ", startDate='" + startDate + '\'' +
                ", endDate='" + endDate + '\'' +
                ", liabilityLimit='" + liabilityLimit + '\'' +
                ", insuranceCoverage=" + insuranceCoverage +
                ", autoRenewal=" + autoRenewal +
                ", hasTerminationClause=" + hasTerminationClause +
                ", termLengthYears=" + termLengthYears +
                '}';
    }
}
