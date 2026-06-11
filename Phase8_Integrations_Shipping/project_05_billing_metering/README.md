# Project 05: Usage Billing & Metering

## What This Does

A complete AI usage billing system: tracks every LLM call by token count, calculates costs, generates invoices, visualizes consumption, and simulates the Stripe payment flow.

## How Token-Based Billing Works

### Why Token-Based?

AI APIs charge by **token** — not by request or time. This is because:
- A 10-word prompt costs ~13 tokens to process
- A 10,000-word document costs ~13,000 tokens
- Charging per-request would massively under-price large requests

One **token** ≈ 4 characters ≈ 0.75 words. Our `estimate_tokens` rule
(word_count × 1.3, rounded) maps "Hello, world!" (2 words) → 3 tokens.

### The Billing Pipeline

```
User sends request
       ↓
MeteringMiddleware intercepts the request
       ↓
Estimates input tokens from request body
       ↓
Request processed by your AI endpoint
       ↓
Middleware intercepts the response
       ↓
Estimates output tokens from response body
       ↓
UsageEvent logged to database with:
  - tenant_id, model, input_tokens, output_tokens, cost_usd, timestamp
       ↓
At month end: InvoiceGenerator aggregates events → Invoice
       ↓
StripeSimulator creates invoice → charges customer
```

### Pricing Model (Simulated)

| Model | Input per 1K tokens | Output per 1K tokens |
|-------|--------------------|-----------------------|
| gemma3:4b | $0.0001 | $0.0003 |
| llama3.2:3b | $0.00008 | $0.00025 |
| mistral:7b | $0.00015 | $0.00045 |
| gpt-4o (reference) | $0.005 | $0.015 |
| claude-3-5-sonnet (reference) | $0.003 | $0.015 |

Output tokens are more expensive because generating text is computationally heavier than reading it.

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the billing dashboard
python billing.py

# Run the Stripe simulation demo
python stripe_integration.py
```

## Usage Metering Architecture

### Adding MeteringMiddleware to Your FastAPI App

```python
from billing import MeteringMiddleware, UsageDatabase, PricingEngine

usage_db = UsageDatabase()
pricing = PricingEngine()

app = FastAPI()
app.add_middleware(MeteringMiddleware, usage_db=usage_db, pricing=pricing)
```

The middleware automatically intercepts every `/chat` request and logs a `UsageEvent`. No changes needed to your endpoint code.

### Generating an Invoice

```python
from billing import UsageDatabase, PricingEngine, InvoiceGenerator
from datetime import datetime

db = UsageDatabase()
pricing = PricingEngine()
gen = InvoiceGenerator(db, pricing)

invoice = gen.generate_invoice("acme-corp", month=5, year=2026)
print(gen.render_invoice(invoice))
```

## How to Connect Real Stripe

### 1. Install the Stripe Python library
```bash
pip install stripe
```

### 2. Set your API key
```bash
export STRIPE_SECRET_KEY=sk_test_...  # Get from dashboard.stripe.com/apikeys
```

### 3. Replace StripeSimulator with real Stripe calls

The `StripeSimulator` methods map 1:1 to real Stripe. Each method's docstring shows the exact equivalent. For example:

```python
# Simulation (current)
stripe_sim.create_customer(email="...", name="...", tenant_id="...")

# Real Stripe (replacement)
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe.Customer.create(
    email="...",
    name="...",
    metadata={"tenant_id": "..."}  # Stripe passes this back in webhooks
)
```

### 4. Set up Stripe webhooks for payment events

```bash
# Install Stripe CLI for local webhook testing
brew install stripe/stripe-cli/stripe
stripe listen --forward-to localhost:8000/webhook
```

```python
# Webhook endpoint in your FastAPI app
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event.type == "invoice.paid":
        # Reset tenant quota, send receipt email
        pass
    elif event.type == "invoice.payment_failed":
        # Send dunning email, downgrade after 3 failures
        pass
```

## How to Add New Models to the Price Table

In `billing.py`, find `PricingEngine.PRICE_TABLE` and add:

```python
PRICE_TABLE = {
    # ... existing models ...
    "your-new-model:13b": {
        "input": 0.0003,   # $0.30 per million input tokens
        "output": 0.0009,  # $0.90 per million output tokens
    },
}
```

The pricing engine will automatically apply the new rates to usage events for that model. Historical events keep their original cost (already stored in `cost_usd`).

## Token Estimation vs. Exact Counting

This project uses word-count estimation (`word_count * 1.3`). For production billing:

```python
# OpenAI models: use tiktoken
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
tokens = len(enc.encode(text))

# Llama/Mistral models: use transformers tokenizer
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")
tokens = len(tokenizer.encode(text))

# Or: call the API and use response.usage.prompt_tokens
# (Ollama returns this in the response — most reliable approach)
```

## Key Learning Points

1. **Metering before billing** — you can't bill what you don't measure
2. **Middleware for automatic metering** — invisible to endpoint code
3. **Separate input/output pricing** — reflects actual compute cost
4. **Stripe objects map to SaaS entities** — Customer=Tenant, Subscription=Plan
5. **Webhooks for payment events** — never trust the frontend for payment confirmation
6. **Amounts in cents** — never use floats for money; Stripe requires integers
