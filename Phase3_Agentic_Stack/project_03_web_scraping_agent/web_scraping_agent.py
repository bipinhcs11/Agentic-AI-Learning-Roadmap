# ═══════════════════════════════════════════════════════════════
# Project 03 — Web Scraping Agent
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Agent that can fetch and read any web page, then answer
#   questions about the content using local Ollama.
#
# INSTALL FIRST:
#   pip install requests beautifulsoup4 --break-system-packages
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python web_scraping_agent.py
# ═══════════════════════════════════════════════════════════════

import re
import textwrap
from openai import OpenAI

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Missing libraries! Run:")
    print("   pip install requests beautifulsoup4 --break-system-packages")
    exit(1)

# ── Connect to Ollama ─────────────────────────────────────────
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "gemma3:4b"

# ── Store scraped content in memory ──────────────────────────
scraped_pages = {}  # url → cleaned text
current_url = None

# ═══════════════════════════════════════════════════════════════
# WEB SCRAPING — Fetch and clean web page content
# ═══════════════════════════════════════════════════════════════

def scrape_url(url: str) -> tuple[bool, str]:
    """
    Fetch a web page and return clean text.
    Returns (success, content_or_error_message)
    """
    # Add https:// if missing
    if not url.startswith("http"):
        url = "https://" + url

    print(f"  🌐 Fetching: {url}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise: scripts, styles, navigation, ads
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "iframe", "noscript", "meta", "link"]):
            tag.decompose()

        # Get the page title
        title = soup.find("title")
        title_text = title.get_text().strip() if title else "No title"

        # Extract main content
        # Try common content containers first
        content = None
        for selector in ["main", "article", "#content", ".content",
                          "#main-content", ".post-content", "body"]:
            content = soup.find(selector)
            if content:
                break

        if not content:
            content = soup

        # Get clean text
        text = content.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)

        # Truncate to ~4000 chars to fit in context window
        if len(clean_text) > 4000:
            clean_text = clean_text[:4000] + "\n\n[... content truncated ...]"

        result = f"PAGE TITLE: {title_text}\nURL: {url}\n\nCONTENT:\n{clean_text}"
        print(f"  ✅ Scraped {len(clean_text)} characters from '{title_text}'")
        return True, result

    except requests.exceptions.ConnectionError:
        return False, f"Error: Could not connect to {url}. Check your internet connection."
    except requests.exceptions.Timeout:
        return False, f"Error: {url} took too long to respond."
    except requests.exceptions.HTTPError as e:
        return False, f"Error: {url} returned status {e.response.status_code}"
    except Exception as e:
        return False, f"Error scraping {url}: {e}"


# ═══════════════════════════════════════════════════════════════
# AGENT — Answer questions about scraped content
# ═══════════════════════════════════════════════════════════════

def agent_respond(question: str, page_content: str) -> str:
    """Ask the AI a question about the scraped page content."""

    messages = [
        {
            "role": "system",
            "content": """You are a helpful research assistant.
You will be given web page content and asked questions about it.
Answer based ONLY on the provided content.
If the answer isn't in the content, say so clearly.
Be concise and factual."""
        },
        {
            "role": "user",
            "content": f"""Here is a web page I scraped:

{page_content}

---
Question: {question}

Answer based on the content above:"""
        }
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════
# MAIN INTERFACE
# ═══════════════════════════════════════════════════════════════

def print_help():
    print("""
Commands:
  scrape <url>     — Fetch and read a web page
  ask <question>   — Ask a question about the last scraped page
  list             — Show all scraped pages
  show             — Show current page content summary
  quit             — Exit

Examples:
  scrape https://en.wikipedia.org/wiki/Python_(programming_language)
  ask What are the main uses of Python?

  scrape https://news.ycombinator.com
  ask What are the top 3 stories?
""")


def main():
    global current_url

    print("=" * 60)
    print("🌐 Web Scraping Agent — Phase 3, Project 3")
    print("=" * 60)
    print(f"Model: {MODEL} (local via Ollama)")
    print_help()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ""

        # ── scrape command ───────────────────────────────────
        if command == "scrape":
            if not argument:
                print("❌ Please provide a URL. Example: scrape https://wikipedia.org")
                continue

            success, content = scrape_url(argument.strip())
            if success:
                url_key = argument.strip()
                scraped_pages[url_key] = content
                current_url = url_key
                # Show a brief preview
                preview = content[:300].replace("\n", " ")
                print(f"\n📄 Preview: {preview}...")
                print(f"\n✅ Page loaded! Now use 'ask <your question>' to query it.")
            else:
                print(f"❌ {content}")

        # ── ask command ──────────────────────────────────────
        elif command == "ask":
            if not argument:
                print("❌ Please provide a question. Example: ask What is the main topic?")
                continue
            if not current_url or current_url not in scraped_pages:
                print("❌ No page loaded yet. Use 'scrape <url>' first.")
                continue

            print("🤔 Thinking...", end="", flush=True)
            try:
                response = agent_respond(argument, scraped_pages[current_url])
                print(" done")
                print(f"\n🤖 Agent: {response}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Make sure 'ollama serve' is running.")

        # ── list command ─────────────────────────────────────
        elif command == "list":
            if scraped_pages:
                print("\n📚 Scraped pages:")
                for i, url in enumerate(scraped_pages.keys(), 1):
                    marker = "← current" if url == current_url else ""
                    print(f"  {i}. {url} {marker}")
            else:
                print("No pages scraped yet.")

        # ── show command ─────────────────────────────────────
        elif command == "show":
            if current_url and current_url in scraped_pages:
                print(f"\n📄 Current page: {current_url}")
                content = scraped_pages[current_url]
                print(content[:800] + "..." if len(content) > 800 else content)
            else:
                print("No page currently loaded.")

        # ── help command ─────────────────────────────────────
        elif command in ["help", "h", "?"]:
            print_help()

        # ── quit command ─────────────────────────────────────
        elif command in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break

        else:
            # Maybe they just typed a question without 'ask'
            if current_url and "?" in user_input:
                print("💡 Tip: Use 'ask' before your question. Trying anyway...")
                print("🤔 Thinking...", end="", flush=True)
                try:
                    response = agent_respond(user_input, scraped_pages[current_url])
                    print(" done")
                    print(f"\n🤖 Agent: {response}")
                except Exception as e:
                    print(f"\n❌ Error: {e}")
            else:
                print(f"❓ Unknown command '{command}'. Type 'help' for commands.")


if __name__ == "__main__":
    main()
