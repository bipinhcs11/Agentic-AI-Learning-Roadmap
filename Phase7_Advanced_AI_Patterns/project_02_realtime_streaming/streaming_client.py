"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║          PHASE 7 — PROJECT 2: WEBSOCKET STREAMING CLIENT (Terminal Test)        ║
║                                                                                  ║
║  What this file does:                                                            ║
║    A pure-Python terminal client that connects to the streaming AI server        ║
║    via WebSocket and demonstrates the streaming experience in the console.       ║
║    Tokens print character-by-character as they arrive — no waiting for the       ║
║    full response. At the end, tokens/sec is calculated and displayed.            ║
║                                                                                  ║
║  Usage:                                                                          ║
║    1. Start the server:  uvicorn server:app --reload                             ║
║    2. Run this client:   python streaming_client.py                              ║
║                                                                                  ║
║  The client runs 3 demo prompts automatically, then exits.                       ║
║  Press Ctrl+C at any time to stop.                                               ║
║                                                                                  ║
║  Dependencies: pip install websockets                                            ║
║  Author : Bipin Pradhan                                                          ║
║  Phase  : 7 — Advanced AI Patterns                                               ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────────
import asyncio
import json
import sys
import time

try:
    import websockets             # pip install websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("[ERROR] Missing 'websockets' package. Install with:  pip install websockets")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────────
SERVER_WS_URL = "ws://localhost:8000/ws/chat"

# Demo prompts — chosen to show different streaming characteristics:
# Short answer (fast), medium answer, long answer (you can see streaming clearly)
DEMO_PROMPTS = [
    "What is a WebSocket and how does it differ from HTTP? Give a one-paragraph explanation.",
    "Explain what makes AI token streaming feel faster to users, even if total generation time is the same.",
    "List 5 real-world applications of real-time AI streaming interfaces, with one sentence each.",
]

# ANSI color codes for terminal output — makes the demo visually clear
RESET  = "\033[0m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
RED    = "\033[31m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


# ─────────────────────────────────────────────────────────────────────────────────
# STREAMING CLIENT FUNCTION
# ─────────────────────────────────────────────────────────────────────────────────

async def send_and_stream(
    ws: websockets.WebSocketClientProtocol,
    message: str,
) -> dict:
    """
    Send one message to the server and collect the streaming response.

    Returns a dict with:
      text         — the full response text
      token_count  — number of tokens received
      elapsed_sec  — time from first token to done signal
      tokens_per_sec — throughput
    """
    # Send the message as JSON (same format the HTML frontend uses)
    await ws.send(json.dumps({"message": message}))

    full_text = ""
    token_count = 0
    start_time: float | None = None

    # Keep reading messages until we receive a "done" or "error" signal
    while True:
        try:
            raw = await ws.recv()
        except ConnectionClosed:
            print(f"\n{RED}[Client] Connection closed unexpectedly{RESET}")
            break

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            # Shouldn't happen, but handle gracefully
            print(raw, end="", flush=True)
            continue

        msg_type = msg.get("type", "")

        if msg_type == "welcome":
            # Skip welcome — already printed at connection time
            continue

        elif msg_type == "token":
            token = msg.get("text", "")
            if token:
                if start_time is None:
                    start_time = time.perf_counter()
                    print(f"\n{CYAN}", end="", flush=True)

                # Print token immediately as it arrives
                # end="" and flush=True are critical — they prevent buffering
                print(token, end="", flush=True)
                full_text += token
                token_count += 1

        elif msg_type == "done":
            # Stream is complete
            print(RESET, end="", flush=True)   # reset terminal color
            elapsed = time.perf_counter() - (start_time or time.perf_counter())
            tps = token_count / elapsed if elapsed > 0 else 0
            return {
                "text": full_text,
                "token_count": token_count,
                "elapsed_sec": elapsed,
                "tokens_per_sec": tps,
            }

        elif msg_type == "error":
            error_text = msg.get("text", "Unknown error")
            print(f"\n{RED}[Server Error] {error_text}{RESET}")
            return {
                "text": full_text,
                "token_count": token_count,
                "elapsed_sec": 0,
                "tokens_per_sec": 0,
            }

    return {
        "text": full_text,
        "token_count": token_count,
        "elapsed_sec": 0,
        "tokens_per_sec": 0,
    }


async def run_demo() -> None:
    """
    Main demo: connect to the server, send 3 prompts, show streaming results.
    """
    print(f"\n{BOLD}{'═'*68}{RESET}")
    print(f"{BOLD}  Phase 7 · Project 2 — Real-time Streaming WebSocket Client{RESET}")
    print(f"{BOLD}{'═'*68}{RESET}")
    print(f"\nConnecting to {SERVER_WS_URL} …")

    try:
        # websockets.connect returns an async context manager
        # The connection is held open for all 3 prompts (efficient — no reconnect overhead)
        async with websockets.connect(
            SERVER_WS_URL,
            open_timeout=10,
            ping_interval=20,   # keep-alive pings every 20s
        ) as ws:
            print(f"{GREEN}Connected!{RESET}")

            # Read and display the welcome message
            welcome_raw = await ws.recv()
            try:
                welcome = json.loads(welcome_raw)
                print(f"{DIM}Server: {welcome.get('text', '')}{RESET}\n")
            except json.JSONDecodeError:
                pass

            # ── Run each demo prompt ───────────────────────────────────────────────
            for i, prompt in enumerate(DEMO_PROMPTS, 1):
                print(f"\n{BOLD}{'─'*68}{RESET}")
                print(f"{YELLOW}Prompt {i}/{len(DEMO_PROMPTS)}:{RESET}")
                print(f"  {prompt}")
                print(f"{BOLD}{'─'*68}{RESET}")
                print(f"{DIM}Streaming response:{RESET}")

                # Stream the response
                stats = await send_and_stream(ws, prompt)

                # ── Print performance stats ────────────────────────────────────────
                print(f"\n\n{DIM}{'─'*40}{RESET}")
                print(
                    f"{DIM}Stats: {stats['token_count']} tokens · "
                    f"{stats['tokens_per_sec']:.1f} tok/s · "
                    f"{stats['elapsed_sec']:.1f}s{RESET}"
                )

                # Pause between prompts so the output is readable
                if i < len(DEMO_PROMPTS):
                    print(f"\n{DIM}Next prompt in 2 seconds…{RESET}")
                    await asyncio.sleep(2)

            print(f"\n{BOLD}{'═'*68}{RESET}")
            print(f"{GREEN}All {len(DEMO_PROMPTS)} demo prompts completed.{RESET}")
            print(f"\nKey observation:")
            print(f"  You saw text appear token-by-token, not all at once.")
            print(f"  This is streaming — the server pushes each token through")
            print(f"  the WebSocket as soon as Ollama generates it.")
            print(f"{'═'*68}\n")

    except ConnectionRefusedError:
        print(f"\n{RED}[ERROR] Could not connect to {SERVER_WS_URL}{RESET}")
        print(f"  Make sure the server is running:")
        print(f"  {YELLOW}uvicorn server:app --reload{RESET}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user.{RESET}")


# ─────────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Synchronous entry point — starts the async event loop."""
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
