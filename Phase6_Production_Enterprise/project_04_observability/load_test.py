# ═══════════════════════════════════════════════════════════════
# load_test.py — AI Platform Load Generator
# Phase 6 · Project 04 Observability
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Sends 30 POST requests to the /chat endpoint with varied prompts.
#   Tracks success/failure counts and latency stats.
#   Prints progress every 5 requests and a final summary.
#
# HOW TO RUN:
#   python load_test.py
#
# DEPS: only 'requests' and 'time' (stdlib + requests)
#   pip install requests
#
# WATCH METRICS LIVE:
#   Open Grafana at http://localhost:3000 while this runs.
#   The "Request Rate", "Active Requests", and "Tokens" panels
#   should all show a spike as requests flow through.
# ═══════════════════════════════════════════════════════════════

import time
import requests

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
API_URL        = "http://localhost:8000/chat"
TOTAL_REQUESTS = 30
DELAY_BETWEEN  = 1.0   # seconds between requests (be gentle with Ollama)

# ─────────────────────────────────────────────────────────────
# Diverse prompts — cycles through all 10 across 30 requests
# ─────────────────────────────────────────────────────────────
PROMPTS = [
    "Explain what a transformer model is in two sentences.",
    "What is the difference between supervised and unsupervised learning?",
    "Name three real-world applications of natural language processing.",
    "What does 'inference' mean in the context of machine learning?",
    "Explain gradient descent like I am a high school student.",
    "What is overfitting and how do you prevent it?",
    "In one paragraph, describe how attention mechanisms work.",
    "What is the purpose of a validation set during model training?",
    "Compare BERT and GPT at a high level.",
    "Why does batch normalization help neural network training?",
]

# ─────────────────────────────────────────────────────────────
# Tracking variables
# ─────────────────────────────────────────────────────────────
results = {
    "success": 0,
    "failure": 0,
    "latencies_ms": [],
    "errors": [],
}

print("=" * 60)
print("  AI Platform Load Test")
print(f"  Target : {API_URL}")
print(f"  Sending: {TOTAL_REQUESTS} requests")
print(f"  Delay  : {DELAY_BETWEEN}s between requests")
print("=" * 60)
print()

# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────
overall_start = time.time()

for i in range(1, TOTAL_REQUESTS + 1):
    prompt = PROMPTS[(i - 1) % len(PROMPTS)]
    payload = {"message": prompt}

    req_start = time.time()
    try:
        response = requests.post(API_URL, json=payload, timeout=130)
        elapsed_ms = (time.time() - req_start) * 1000

        if response.status_code == 200:
            data = response.json()
            results["success"] += 1
            results["latencies_ms"].append(elapsed_ms)
            status_str = f"OK  {elapsed_ms:7.0f}ms  ~{data.get('tokens_estimated', '?')} tokens"
        else:
            results["failure"] += 1
            err_msg = f"HTTP {response.status_code}"
            results["errors"].append(err_msg)
            status_str = f"FAIL  {err_msg}"

    except requests.Timeout:
        elapsed_ms = (time.time() - req_start) * 1000
        results["failure"] += 1
        results["errors"].append("Timeout")
        status_str = f"FAIL  Timeout after {elapsed_ms:.0f}ms"

    except requests.ConnectionError:
        results["failure"] += 1
        results["errors"].append("ConnectionError")
        status_str = "FAIL  Connection refused — is the API running?"

    except Exception as exc:
        results["failure"] += 1
        results["errors"].append(str(exc))
        status_str = f"FAIL  {exc}"

    # Per-request line
    print(f"  [{i:02d}/{TOTAL_REQUESTS}] {status_str}")
    print(f"         Prompt: \"{prompt[:55]}{'...' if len(prompt) > 55 else ''}\"")

    # Progress summary every 5 requests
    if i % 5 == 0:
        completed = results["success"] + results["failure"]
        success_rate = (results["success"] / completed * 100) if completed else 0
        avg_ms = (
            sum(results["latencies_ms"]) / len(results["latencies_ms"])
            if results["latencies_ms"] else 0
        )
        print()
        print(f"  --- Progress [{i}/{TOTAL_REQUESTS}] ---")
        print(f"      Success rate : {success_rate:.1f}%")
        print(f"      Avg latency  : {avg_ms:.0f}ms")
        print(f"      Failures so far: {results['failure']}")
        print()

    # Pace the requests
    if i < TOTAL_REQUESTS:
        time.sleep(DELAY_BETWEEN)

# ─────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────
total_elapsed = time.time() - overall_start
latencies = results["latencies_ms"]

print()
print("=" * 60)
print("  FINAL SUMMARY")
print("=" * 60)
print(f"  Total requests  : {TOTAL_REQUESTS}")
print(f"  Successful      : {results['success']}")
print(f"  Failed          : {results['failure']}")

if results["success"] > 0:
    success_rate = results["success"] / TOTAL_REQUESTS * 100
    avg_ms   = sum(latencies) / len(latencies)
    min_ms   = min(latencies)
    max_ms   = max(latencies)

    # P95: sort and take the 95th percentile value
    sorted_lat = sorted(latencies)
    p95_idx    = int(len(sorted_lat) * 0.95)
    p95_ms     = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

    print(f"  Success rate    : {success_rate:.1f}%")
    print(f"  Total wall time : {total_elapsed:.1f}s")
    print()
    print("  Latency (successful requests only):")
    print(f"    Min  : {min_ms:.0f}ms")
    print(f"    Avg  : {avg_ms:.0f}ms")
    print(f"    P95  : {p95_ms:.0f}ms")
    print(f"    Max  : {max_ms:.0f}ms")

if results["errors"]:
    from collections import Counter
    error_counts = Counter(results["errors"])
    print()
    print("  Error breakdown:")
    for err, count in error_counts.most_common():
        print(f"    {err}: {count}x")

print()
print("  Check Grafana at http://localhost:3000 to see the spike")
print("  in Request Rate, Tokens, and Latency panels.")
print("=" * 60)
