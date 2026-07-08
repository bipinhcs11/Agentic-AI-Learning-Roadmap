package com.benefits.adk.ucp;

import java.util.List;

// The UCP "order": the confirmation artifact produced only after checkout.
// The pay statement preview is the human-facing part of the receipt.
public record EnrollmentReceipt(
        String confirmationId,
        String effectiveDate,
        Payslip payslip,
        List<String> notes
) {
    public EnrollmentReceipt {
        notes = notes == null ? List.of() : List.copyOf(notes);
    }
}
