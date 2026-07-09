package com.benefits.adk.ucp;

// The states of the UCP benefits transaction lane:
// PROPOSED -> PENDING_APPROVAL -> APPROVED -> ENROLLED, with BLOCKED as the
// terminal state whenever the human approval gate is not satisfied.
public enum TransactionStatus {
    PROPOSED,
    PENDING_APPROVAL,
    APPROVED,
    ENROLLED,
    BLOCKED
}
