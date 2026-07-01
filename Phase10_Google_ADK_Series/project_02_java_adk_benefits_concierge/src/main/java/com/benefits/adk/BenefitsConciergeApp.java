package com.benefits.adk;

public final class BenefitsConciergeApp {
    private BenefitsConciergeApp() {
    }

    public static void main(String[] args) {
        var agent = BenefitsConciergeAgent.createAgent();
        System.out.println("Created Java ADK agent: " + agent.name());
        System.out.println("Model: " + BenefitsConciergeAgent.MODEL);
        System.out.println("Rung 01A is text-only. Run it in ADK Dev UI with Gemini credentials configured.");
    }
}
