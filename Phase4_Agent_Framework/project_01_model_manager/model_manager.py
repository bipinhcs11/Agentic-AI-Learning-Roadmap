# ═══════════════════════════════════════════════════════════════
# Project 01 — Model Manager
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Manage your local Ollama models programmatically.
#   This is how Open WebUI and similar tools work under the hood!
#
# INSTALL FIRST:
#   pip install requests rich --break-system-packages
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python model_manager.py
# ═══════════════════════════════════════════════════════════════

import sys
import json
from datetime import datetime

try:
    import requests
except ImportError:
    print("Install requests: pip install requests --break-system-packages")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("💡 Tip: Install rich for prettier output: pip install rich --break-system-packages")

OLLAMA_BASE = "http://localhost:11434"
console = Console() if HAS_RICH else None


# ═══════════════════════════════════════════════════════════════
# OLLAMA API WRAPPER
# ═══════════════════════════════════════════════════════════════

def ollama_get(endpoint: str) -> dict:
    """Make a GET request to the Ollama API."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {OLLAMA_BASE}")
        print("   Make sure 'ollama serve' is running!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ API error: {e}")
        return {}


def ollama_post(endpoint: str, data: dict) -> dict:
    """Make a POST request to the Ollama API."""
    try:
        resp = requests.post(f"{OLLAMA_BASE}{endpoint}", json=data, timeout=300)
        resp.raise_for_status()
        # Handle streaming JSON lines
        if resp.headers.get("Content-Type", "").startswith("application/x-ndjson"):
            lines = resp.text.strip().split("\n")
            return json.loads(lines[-1]) if lines else {}
        return resp.json()
    except requests.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {OLLAMA_BASE}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ API error: {e}")
        return {}


def ollama_delete(endpoint: str, data: dict) -> bool:
    """Make a DELETE request to the Ollama API."""
    try:
        resp = requests.delete(f"{OLLAMA_BASE}{endpoint}", json=data, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════

def cmd_list():
    """List all installed models."""
    print("\n📦 Fetching installed models...")
    data = ollama_get("/api/tags")
    models = data.get("models", [])

    if not models:
        print("No models installed. Try: python model_manager.py pull gemma3:4b")
        return

    if HAS_RICH:
        table = Table(title=f"Installed Models ({len(models)} total)")
        table.add_column("Model Name", style="cyan", no_wrap=True)
        table.add_column("Size", style="green", justify="right")
        table.add_column("Family", style="yellow")
        table.add_column("Modified", style="dim")

        for m in models:
            name = m.get("name", "?")
            size_bytes = m.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)
            size_str = f"{size_gb:.1f} GB" if size_gb >= 1 else f"{size_bytes/(1024**2):.0f} MB"
            family = m.get("details", {}).get("family", "?")
            modified = m.get("modified_at", "")[:10]
            table.add_row(name, size_str, family, modified)

        console.print(table)
    else:
        print(f"\n{'MODEL':<35} {'SIZE':>10} {'FAMILY':<15}")
        print("-" * 65)
        for m in models:
            name = m.get("name", "?")
            size_bytes = m.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)
            size_str = f"{size_gb:.1f} GB" if size_gb >= 1 else f"{size_bytes/(1024**2):.0f} MB"
            family = m.get("details", {}).get("family", "?")
            print(f"{name:<35} {size_str:>10} {family:<15}")


def cmd_info(model_name: str):
    """Show detailed info about a model."""
    print(f"\n🔍 Getting info for: {model_name}")
    data = ollama_post("/api/show", {"name": model_name})

    if not data:
        print(f"❌ Model '{model_name}' not found. Run 'list' to see installed models.")
        return

    details = data.get("details", {})

    if HAS_RICH:
        info = {
            "Family": details.get("family", "?"),
            "Parameters": details.get("parameter_size", "?"),
            "Quantization": details.get("quantization_level", "?"),
            "Format": details.get("format", "?"),
        }
        panel_content = "\n".join(f"[cyan]{k}:[/cyan] {v}" for k, v in info.items())
        console.print(Panel(panel_content, title=f"[bold]{model_name}[/bold]"))
    else:
        print(f"\n  Model:          {model_name}")
        print(f"  Family:         {details.get('family', '?')}")
        print(f"  Parameters:     {details.get('parameter_size', '?')}")
        print(f"  Quantization:   {details.get('quantization_level', '?')}")

    # Show modelfile snippet
    modelfile = data.get("modelfile", "")
    if modelfile:
        print(f"\n  Modelfile (first 300 chars):")
        print("  " + modelfile[:300].replace("\n", "\n  "))


def cmd_pull(model_name: str):
    """Download a model from Ollama library."""
    print(f"\n⬇️  Pulling model: {model_name}")
    print("   This may take several minutes for large models...")
    print("   (Progress is shown in the Ollama terminal)")

    # Stream the pull progress
    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/pull",
            json={"name": model_name},
            stream=True,
            timeout=600
        )

        last_status = ""
        for line in resp.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if status != last_status and status:
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        if total > 0:
                            pct = (completed / total) * 100
                            print(f"  {status}: {pct:.1f}%", end="\r")
                        else:
                            print(f"  {status}        ", end="\r")
                        last_status = status
                except Exception:
                    pass

        print(f"\n✅ Successfully pulled: {model_name}")

    except requests.ConnectionError:
        print(f"❌ Cannot connect to Ollama. Make sure 'ollama serve' is running.")
    except Exception as e:
        print(f"❌ Pull failed: {e}")


def cmd_delete(model_name: str):
    """Delete a model."""
    confirm = input(f"⚠️  Delete '{model_name}'? This cannot be undone. (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return

    success = ollama_delete("/api/delete", {"name": model_name})
    if success:
        print(f"✅ Deleted: {model_name}")
    else:
        print(f"❌ Failed to delete '{model_name}'. Is it installed?")


def cmd_test(model_name: str):
    """Quick test — generate a short response."""
    print(f"\n🧪 Testing model: {model_name}")
    print("   Sending: 'Say hello in one sentence'")

    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": model_name, "prompt": "Say hello in one sentence.", "stream": False},
            timeout=60
        )
        data = resp.json()
        response = data.get("response", "No response")
        duration_ns = data.get("total_duration", 0)
        duration_s = duration_ns / 1e9

        print(f"\n   Response: {response}")
        print(f"   Time: {duration_s:.2f}s")
        print(f"\n✅ Model '{model_name}' is working!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


def cmd_status():
    """Show Ollama server status."""
    print("\n🔍 Checking Ollama status...")
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/version", timeout=5)
        data = resp.json()
        version = data.get("version", "unknown")
        print(f"✅ Ollama is running")
        print(f"   Version: {version}")
        print(f"   URL: {OLLAMA_BASE}")

        # Count models
        models_data = ollama_get("/api/tags")
        count = len(models_data.get("models", []))
        print(f"   Models installed: {count}")

    except requests.ConnectionError:
        print(f"❌ Ollama is NOT running at {OLLAMA_BASE}")
        print("   Start it with: ollama serve")


def print_help():
    print("""
Model Manager — Ollama API Controller

Usage: python model_manager.py [command] [model_name]

Commands:
  list                  Show all installed models
  info  <model>         Show detailed model info
  pull  <model>         Download a model
  delete <model>        Delete a model
  test  <model>         Quick test a model
  status                Check Ollama server status

Examples:
  python model_manager.py list
  python model_manager.py info gemma3:4b
  python model_manager.py pull llama3.2:3b
  python model_manager.py test gemma3:4b
  python model_manager.py delete llama3.2:3b
""")


def interactive_menu():
    """Interactive menu when no command given."""
    print("=" * 55)
    print("📦 Model Manager — Phase 4, Project 1")
    print("=" * 55)
    cmd_status()

    print("\nCommands: list | info <model> | pull <model> | delete <model> | test <model> | quit")

    while True:
        try:
            user_input = input("\n> ").strip().split()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input[0].lower()
        arg = user_input[1] if len(user_input) > 1 else ""

        if cmd == "list":           cmd_list()
        elif cmd == "info":         cmd_info(arg) if arg else print("Usage: info <model_name>")
        elif cmd == "pull":         cmd_pull(arg) if arg else print("Usage: pull <model_name>")
        elif cmd == "delete":       cmd_delete(arg) if arg else print("Usage: delete <model_name>")
        elif cmd == "test":         cmd_test(arg) if arg else print("Usage: test <model_name>")
        elif cmd == "status":       cmd_status()
        elif cmd in ["help", "?"]:  print_help()
        elif cmd in ["quit", "exit", "q"]: print("👋 Goodbye!"); break
        else: print(f"Unknown command: {cmd}. Type 'help' for commands.")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        interactive_menu()
    elif args[0] == "list":         cmd_list()
    elif args[0] == "status":       cmd_status()
    elif args[0] == "info" and len(args) > 1:    cmd_info(args[1])
    elif args[0] == "pull" and len(args) > 1:    cmd_pull(args[1])
    elif args[0] == "delete" and len(args) > 1:  cmd_delete(args[1])
    elif args[0] == "test" and len(args) > 1:    cmd_test(args[1])
    else:
        print_help()
