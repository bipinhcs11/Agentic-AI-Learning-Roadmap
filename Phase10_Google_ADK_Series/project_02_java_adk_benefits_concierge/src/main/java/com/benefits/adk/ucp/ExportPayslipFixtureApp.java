package com.benefits.adk.ucp;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

// Prints the Module 02 mock pay statement as an A2UI payload, so a checked-in
// fixture can be regenerated for the React renderer. Mirrors
// com.benefits.adk.ExportA2uiFixtureApp.
//
//   mvn -q -o exec:java \
//     -Dexec.mainClass=com.benefits.adk.ucp.ExportPayslipFixtureApp
public final class ExportPayslipFixtureApp {
    private ExportPayslipFixtureApp() {
    }

    public static void main(String[] args) throws Exception {
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        var payload = UcpBenefitsTransactionTools.buildPayslipA2ui(
                "Jordan Rivers",
                "EMP-1042",
                "standard",
                90000,
                6,
                6000,
                "family",
                22
        );
        System.out.println(mapper.writeValueAsString(payload));
    }
}
