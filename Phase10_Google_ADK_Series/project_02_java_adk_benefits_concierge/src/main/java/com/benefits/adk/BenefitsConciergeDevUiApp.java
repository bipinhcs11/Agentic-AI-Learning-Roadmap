package com.benefits.adk;

import com.google.adk.web.AdkWebServer;

public final class BenefitsConciergeDevUiApp {
    private BenefitsConciergeDevUiApp() {
    }

    public static void main(String[] args) {
        System.out.println("Starting ADK Dev UI for java_adk_benefits_concierge");
        System.out.println("Open http://localhost:8080 after the server starts.");
        AdkWebServer.start(BenefitsConciergeAgent.createAgent());
    }
}
