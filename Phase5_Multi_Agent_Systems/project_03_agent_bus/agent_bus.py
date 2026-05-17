# ═══════════════════════════════════════════════════════════════
# Project 03 — Agent Communication Bus
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds an event-driven agent pipeline where agents communicate
#   through a message bus — NOT through a central supervisor.
#
#   Each agent:
#     - SUBSCRIBES to a topic (e.g. "raw_content")
#     - Does its work when a message arrives
#     - PUBLISHES its output to the next topic
#
#   No agent knows about other agents. They only know their
#   input topic and output topic. This is loose coupling.
#
# MESSAGE FLOW:
#
#   [User] → topic:"user_requests"
#       ↓
#   [Fetcher Agent]  listens on "user_requests"
#       → publishes to "raw_content"
#       ↓
#   [Analyzer Agent] listens on "raw_content"
#       → publishes to "analyzed_content"
#       ↓
#   [Reporter Agent] listens on "analyzed_content"
#       → publishes to "final_reports"
#       ↓
#   [User sees result]
#
# KEY CONCEPTS:
#   - Message Bus: a channel where agents publish/subscribe
#   - Pub/Sub pattern: publishers don't know who's listening
#   - Event-driven: agents react to messages, not called directly
#   - Loose coupling: swap any agent without changing others
#   - asyncio: Python's async/await for concurrent agents
#
# TWO BACKENDS (swap freely):
#   1. InMemoryBus  — asyncio queues, no setup needed (default)
#   2. RedisBus     — Redis Pub/Sub, requires: brew install redis
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python agent_bus.py
#
#   Optional (for Redis backend):
#   brew install redis && brew services start redis
# ═══════════════════════════════════════════════════════════════

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine
from openai import OpenAI

# ─────────────────────────────────────────────────────────────
# SETUP: Ollama client (sync — we'll wrap in asyncio.to_thread)
# ─────────────────────────────────────────────────────────────

ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "gemma3:4b"


# ═══════════════════════════════════════════════════════════════
# STEP 1: MESSAGE DATACLASS
#
# Every message on the bus has the same structure.
# Agents don't care who sent it — they only read the payload.
# ═══════════════════════════════════════════════════════════════

@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    sender: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "sender": self.sender,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(**d)


# ═══════════════════════════════════════════════════════════════
# STEP 2: MESSAGE BUS (Abstract Base + Two Implementations)
#
# We define an abstract interface first, then implement it twice:
#   - InMemoryBus: asyncio queues (no dependencies)
#   - RedisBus: Redis Pub/Sub (requires Redis server)
#
# Both implement the same interface so agents don't care which
# backend is running. This is the "Dependency Inversion" principle.
# ═══════════════════════════════════════════════════════════════

class MessageBus(ABC):
    """Abstract message bus interface."""

    @abstractmethod
    async def publish(self, topic: str, message: Message) -> None:
        """Publish a message to a topic."""

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to a topic with a handler coroutine."""

    @abstractmethod
    async def start(self) -> None:
        """Start the bus (begin routing messages)."""

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down the bus."""


class InMemoryBus(MessageBus):
    """
    Asyncio queue-based message bus.
    Perfect for development and learning — zero dependencies.

    Each topic has a queue. When you publish, messages go in.
    Subscribers are coroutines that process messages as they arrive.
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def publish(self, topic: str, message: Message) -> None:
        message.topic = topic
        await self._queues[topic].put(message)
        print(f"  [BUS] Published → {topic} (msg_id: {message.id})")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        self._handlers[topic].append(handler)

    async def _process_topic(self, topic: str) -> None:
        """Worker loop: pull messages from a queue and call all handlers."""
        queue = self._queues[topic]
        while self._running:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=0.5)
                for handler in self._handlers[topic]:
                    await handler(message)
                queue.task_done()
            except asyncio.TimeoutError:
                continue  # no messages yet, keep waiting

    async def start(self) -> None:
        self._running = True
        # Create a processing loop for every topic that has handlers
        for topic in self._handlers:
            task = asyncio.create_task(self._process_topic(topic))
            self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


class RedisBus(MessageBus):
    """
    Redis Pub/Sub message bus.
    Use this when you want agents running on DIFFERENT machines.

    Requires: brew install redis && brew services start redis
    Then: pip install redis
    """

    def __init__(self, host: str = "localhost", port: int = 6379):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.Redis(host=host, port=port, decode_responses=True)
            self._pubsub = None
            self._handlers: dict[str, list[Callable]] = defaultdict(list)
            self._running = False
            self._available = True
        except ImportError:
            self._available = False

    async def publish(self, topic: str, message: Message) -> None:
        if not self._available:
            raise RuntimeError("Redis not available. Use InMemoryBus.")
        await self._redis.publish(topic, json.dumps(message.to_dict()))
        print(f"  [REDIS BUS] Published → {topic}")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        self._handlers[topic].append(handler)

    async def start(self) -> None:
        import redis.asyncio as aioredis
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(*self._handlers.keys())
        self._running = True

        async def listener():
            async for raw_msg in self._pubsub.listen():
                if raw_msg["type"] == "message":
                    topic = raw_msg["channel"]
                    message = Message.from_dict(json.loads(raw_msg["data"]))
                    for handler in self._handlers.get(topic, []):
                        await handler(message)

        asyncio.create_task(listener())

    async def stop(self) -> None:
        self._running = False
        if self._pubsub:
            await self._pubsub.unsubscribe()
        await self._redis.aclose()


# ═══════════════════════════════════════════════════════════════
# STEP 3: THE AGENTS
#
# Each agent is a class with:
#   - input_topic:  what it listens to
#   - output_topic: where it publishes results
#   - process():    the async method that does the actual work
#
# Agents register themselves with the bus via subscribe().
# They're completely decoupled — no agent references another.
# ═══════════════════════════════════════════════════════════════

class FetcherAgent:
    """
    Fetches/generates raw content about a topic.
    Listens on: user_requests
    Publishes to: raw_content
    """
    name = "fetcher"
    input_topic = "user_requests"
    output_topic = "raw_content"

    def __init__(self, bus: MessageBus):
        self.bus = bus

    async def register(self):
        await self.bus.subscribe(self.input_topic, self.handle)

    async def handle(self, message: Message) -> None:
        topic = message.payload.get("topic", "unknown")
        print(f"\n  [FETCHER] Processing request for: {topic}")

        # Call Ollama in a thread (it's sync, we're in async context)
        def fetch():
            response = ollama.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a content gatherer. Produce raw, detailed information about the given topic. Include facts, context, and examples. Do not summarize — just gather."},
                    {"role": "user", "content": f"Gather comprehensive raw information about: {topic}"},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content

        raw_content = await asyncio.to_thread(fetch)
        print(f"  [FETCHER] Done — fetched {len(raw_content)} chars")

        # Publish result to the next topic
        await self.bus.publish(self.output_topic, Message(
            sender=self.name,
            payload={
                "topic": topic,
                "raw_content": raw_content,
                "original_request_id": message.id,
            }
        ))


class AnalyzerAgent:
    """
    Analyzes raw content and extracts key insights.
    Listens on: raw_content
    Publishes to: analyzed_content
    """
    name = "analyzer"
    input_topic = "raw_content"
    output_topic = "analyzed_content"

    def __init__(self, bus: MessageBus):
        self.bus = bus

    async def register(self):
        await self.bus.subscribe(self.input_topic, self.handle)

    async def handle(self, message: Message) -> None:
        topic = message.payload.get("topic", "unknown")
        raw_content = message.payload.get("raw_content", "")
        print(f"\n  [ANALYZER] Analyzing content about: {topic}")

        def analyze():
            response = ollama.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a sharp analyst. Extract the most important insights, trends, and implications from raw content. Be specific — avoid vague generalizations."},
                    {"role": "user", "content": f"Analyze this raw content about {topic}:\n\n{raw_content[:3000]}\n\nExtract: top insights, key trends, surprising findings, and strategic implications."},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content

        analysis = await asyncio.to_thread(analyze)
        print(f"  [ANALYZER] Done — {len(analysis)} chars of analysis")

        await self.bus.publish(self.output_topic, Message(
            sender=self.name,
            payload={
                "topic": topic,
                "raw_content": raw_content,
                "analysis": analysis,
                "original_request_id": message.payload.get("original_request_id"),
            }
        ))


class ReporterAgent:
    """
    Writes a final report from analyzed content.
    Listens on: analyzed_content
    Publishes to: final_reports
    """
    name = "reporter"
    input_topic = "analyzed_content"
    output_topic = "final_reports"

    def __init__(self, bus: MessageBus, results: list):
        self.bus = bus
        self.results = results  # shared list to collect completed reports

    async def register(self):
        await self.bus.subscribe(self.input_topic, self.handle)

    async def handle(self, message: Message) -> None:
        topic = message.payload.get("topic", "unknown")
        analysis = message.payload.get("analysis", "")
        print(f"\n  [REPORTER] Writing report about: {topic}")

        def write():
            response = ollama.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional report writer. Create clear, well-structured reports from analytical findings. Use headers, bullet points, and concrete language."},
                    {"role": "user", "content": f"Write a professional report on '{topic}' based on this analysis:\n\n{analysis}\n\nInclude: Summary, Key Findings, Implications, and Recommendations."},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content

        report = await asyncio.to_thread(write)
        print(f"  [REPORTER] Done — final report ready ({len(report)} chars)")

        result = {
            "topic": topic,
            "report": report,
            "completed_at": datetime.now().isoformat(),
        }
        self.results.append(result)

        await self.bus.publish(self.output_topic, Message(
            sender=self.name,
            payload=result
        ))


# ═══════════════════════════════════════════════════════════════
# STEP 4: WIRE IT ALL TOGETHER
# ═══════════════════════════════════════════════════════════════

async def run_pipeline(topic: str) -> dict:
    """Run the full event-driven agent pipeline."""

    print(f"\n{'═'*60}")
    print(f"  AGENT COMMUNICATION BUS — Event-Driven Pipeline")
    print(f"{'═'*60}")
    print(f"  Topic: {topic}")
    print(f"  Backend: InMemoryBus (asyncio queues)")
    print(f"\n  Flow: user_requests → raw_content → analyzed_content → final_reports")
    print(f"{'═'*60}\n")

    # Create the bus
    bus = InMemoryBus()
    results = []

    # Create and register agents
    fetcher  = FetcherAgent(bus)
    analyzer = AnalyzerAgent(bus)
    reporter = ReporterAgent(bus, results)

    await fetcher.register()
    await analyzer.register()
    await reporter.register()

    # Start the bus (begins routing messages)
    await bus.start()
    print("  [BUS] Started — agents listening on their topics\n")

    # Inject the initial request — this kicks off the whole pipeline
    await bus.publish("user_requests", Message(
        sender="user",
        payload={"topic": topic}
    ))

    # Wait for pipeline to complete (check for result with timeout)
    timeout = 180  # 3 minutes max
    start = time.time()
    while not results and (time.time() - start) < timeout:
        await asyncio.sleep(0.5)

    await bus.stop()

    if results:
        return results[0]
    return {"error": "Pipeline timed out", "topic": topic}


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("  PHASE 5 — PROJECT 03: Agent Communication Bus")
    print("═"*60)
    print("\n  Event-driven pipeline — agents talk via message bus")
    print("  No supervisor! Each agent reacts to its input topic.")
    print("\n  KEY DIFFERENCE from Projects 01 & 02:")
    print("  → No central coordinator")
    print("  → Agents are decoupled — swap any without changing others")
    print("  → Can run agents on different machines with Redis backend")

    topics = [
        "The impact of AI on software developer productivity",
        "Open source vs proprietary AI models in 2025",
        "Edge AI and running models on mobile devices",
    ]

    print("\n  Topics:")
    for i, t in enumerate(topics, 1):
        print(f"  [{i}] {t}")
    print("  [4] Enter your own topic")

    choice = input("\n  Choose (1-4): ").strip()
    if choice in ("1", "2", "3"):
        topic = topics[int(choice) - 1]
    elif choice == "4":
        topic = input("  Enter topic: ").strip()
    else:
        topic = topics[0]

    result = asyncio.run(run_pipeline(topic))

    print("\n" + "═"*60)
    print("  FINAL REPORT")
    print("═"*60)
    if "report" in result:
        print(result["report"])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    print("\n" + "═"*60)
    print("  3 agents ran concurrently via the message bus.")
    print("  To use Redis backend: set RedisBus() instead of InMemoryBus()")
    print("═"*60)


if __name__ == "__main__":
    main()
