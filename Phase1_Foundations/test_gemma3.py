"""
test_gemma3.py — Phase 1 verification script
Calls Gemma3 running locally via Ollama's OpenAI-compatible API.
Make sure 'ollama serve' is running before executing this script.
"""

from openai import OpenAI

# Point to local Ollama server (no API key needed)
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # dummy key — Ollama does not require authentication
)

print("Connecting to Ollama at http://localhost:11434 ...")
print("-" * 50)

response = client.chat.completions.create(
    model="gemma3:4b",
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user",   "content": "Explain what an AI agent is in 2 sentences."}
    ]
)

print("Gemma3:27b response:")
print(response.choices[0].message.content)
print("-" * 50)
print("SUCCESS: Gemma3 is working via Ollama API!")
