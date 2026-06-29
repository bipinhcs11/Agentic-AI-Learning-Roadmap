package agentcard

import "testing"

func TestGetCardIncludesTopLevelURL(t *testing.T) {
	t.Setenv("AGENT_URL", "http://go-compliance-agent.test:8888")

	card := GetCard()

	if card.URL != "http://go-compliance-agent.test:8888" {
		t.Fatalf("expected top-level URL from AGENT_URL, got %q", card.URL)
	}
	if len(card.SupportedInterfaces) != 1 {
		t.Fatalf("expected one supported interface, got %d", len(card.SupportedInterfaces))
	}
	if card.SupportedInterfaces[0].URL != card.URL {
		t.Fatalf("expected supported interface URL %q to match top-level URL %q", card.SupportedInterfaces[0].URL, card.URL)
	}
}
