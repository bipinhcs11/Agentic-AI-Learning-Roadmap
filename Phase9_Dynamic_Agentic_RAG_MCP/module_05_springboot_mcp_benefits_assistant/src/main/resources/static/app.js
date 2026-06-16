const form = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question");
const runButton = document.querySelector(".run-button");
const latency = document.querySelector("#latency");
const routeLabel = document.querySelector("#route-label");
const routeBadge = document.querySelector("#route-badge");
const backendLabel = document.querySelector("#backend-label");
const answerText = document.querySelector("#answer");
const toolList = document.querySelector("#tool-list");
const docList = document.querySelector("#doc-list");
const citationList = document.querySelector("#citation-list");
const toolCount = document.querySelector("#tool-count");
const docCount = document.querySelector("#doc-count");
const citationCount = document.querySelector("#citation-count");
const backendStatus = document.querySelector("#backend-status");
const transportStatus = document.querySelector("#transport-status");
const apiStatus = document.querySelector("#api-status");
const debugTransport = document.querySelector("#debug-transport");
const debugEndpoint = document.querySelector("#debug-endpoint");
const debugApi = document.querySelector("#debug-api");
const backendButtons = document.querySelectorAll("[data-backend]");

const routeClasses = ["route-direct", "route-mcp", "route-rag", "route-mcp-rag"];
const BACKENDS = {
  python: {
    label: "Python MCP + RAG router (Module 02)",
    status: "Python active",
    transport: "stdio MCP + demo API",
    statusApi: ":8090 API",
    apiUrl: window.location.port === "8090"
      ? "/api/benefits/agent/ask"
      : "http://localhost:8090/api/benefits/agent/ask",
    debugTransport: "MCP stdio server + local HTTP demo API",
    debugEndpoint: "benefits_mcp_server.py (stdio)",
    debugApi: "http://localhost:8090/api/benefits/agent/ask",
    arc: "python"
  },
  spring: {
    label: "Spring Boot MCP + RAG microservice",
    status: "Spring Boot active",
    transport: "Streamable HTTP",
    statusApi: ":8085 API",
    apiUrl: window.location.port === "8085"
      ? "/api/benefits/agent/ask"
      : "http://localhost:8085/api/benefits/agent/ask",
    debugTransport: "Streamable HTTP",
    debugEndpoint: "http://localhost:8085/mcp",
    debugApi: "http://localhost:8085/api/benefits/agent/ask",
    arc: "spring"
  }
};
let activeBackend = initialBackend();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await ask(questionInput.value);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", async () => {
    questionInput.value = button.dataset.question;
    await ask(button.dataset.question);
  });
});

backendButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    setBackend(button.dataset.backend);
    await ask(questionInput.value);
  });
});

window.addEventListener("DOMContentLoaded", () => {
  renderBackend();
  ask(questionInput.value);
});

async function ask(question) {
  const started = performance.now();
  setBusy(true);
  const backend = BACKENDS[activeBackend];

  try {
    const response = await fetch(backend.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question })
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    render(data);
    latency.textContent = `${Math.max(1, Math.round(performance.now() - started))} ms`;
  } catch (error) {
    renderError(error);
  } finally {
    setBusy(false);
  }
}

function setBusy(isBusy) {
  runButton.disabled = isBusy;
  runButton.querySelector("span:last-child").textContent = isBusy ? "Running" : "Run";
  if (isBusy) {
    latency.textContent = "Running";
  }
}

function render(data) {
  routeLabel.textContent = data.routeLabel || "Direct";
  routeBadge.textContent = data.route || "direct";
  routeBadge.classList.remove(...routeClasses);
  routeBadge.classList.add(routeClass(data.route));
  backendLabel.textContent = data.backend || BACKENDS[activeBackend].label;
  answerText.textContent = data.answer || "No answer returned.";

  renderTools(data.toolCalls || []);
  renderDocuments(data.retrievedDocuments || []);
  renderCitations(data.citations || []);
}

function routeClass(route) {
  if (route === "mcp") {
    return "route-mcp";
  }
  if (route === "rag") {
    return "route-rag";
  }
  if (route === "mcp+rag") {
    return "route-mcp-rag";
  }
  return "route-direct";
}

function renderTools(tools) {
  toolList.replaceChildren();
  toolCount.textContent = tools.length;

  if (tools.length === 0) {
    toolList.append(emptyState("No tool calls for this route."));
    return;
  }

  tools.forEach((tool) => {
    const item = document.createElement("article");
    item.className = "trace-item";

    const meta = document.createElement("div");
    meta.className = "trace-meta";

    const name = document.createElement("span");
    name.className = "trace-name";
    name.textContent = tool.name;

    const target = document.createElement("span");
    target.className = "trace-target";
    target.textContent = `${tool.target} - ${tool.status}`;

    meta.append(name, target);

    const args = document.createElement("pre");
    args.className = "trace-args";
    args.textContent = JSON.stringify(tool.arguments || {}, null, 2);

    item.append(meta, args);
    toolList.append(item);
  });
}

function renderDocuments(docs) {
  docList.replaceChildren();
  docCount.textContent = docs.length;

  if (docs.length === 0) {
    docList.append(emptyState("No documents retrieved for this route."));
    return;
  }

  docs.forEach((doc) => {
    const item = document.createElement("article");
    item.className = "doc-item";

    const meta = document.createElement("div");
    meta.className = "doc-meta";

    const source = document.createElement("span");
    source.className = "doc-source";
    source.textContent = doc.source;

    const score = document.createElement("span");
    score.className = "doc-score";
    score.textContent = `score ${Number(doc.score || 0).toFixed(1)}`;

    meta.append(source, score);

    const heading = document.createElement("p");
    heading.className = "doc-heading";
    heading.textContent = doc.heading;

    const text = document.createElement("p");
    text.className = "doc-text";
    text.textContent = compact(doc.text || "", 210);

    item.append(meta, heading, text);
    docList.append(item);
  });
}

function renderCitations(citations) {
  citationList.replaceChildren();
  citationCount.textContent = citations.length;

  if (citations.length === 0) {
    citationList.append(emptyState("No citations for this route."));
    return;
  }

  citations.forEach((citation) => {
    const link = document.createElement("a");
    const url = extractUrl(citation);
    link.href = url || "#";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = citation;
    citationList.append(link);
  });
}

function renderError(error) {
  routeLabel.textContent = "Offline";
  routeBadge.textContent = "error";
  routeBadge.classList.remove(...routeClasses);
  routeBadge.classList.add("route-direct");
  backendLabel.textContent = BACKENDS[activeBackend].label;
  answerText.textContent = `Could not reach ${BACKENDS[activeBackend].label}. ${error.message}`;
  renderTools([]);
  renderDocuments([]);
  renderCitations([]);
  latency.textContent = "Error";
}

function emptyState(message) {
  const node = document.createElement("p");
  node.className = "empty-state";
  node.textContent = message;
  return node;
}

function compact(text, maxLength) {
  const cleaned = text
    .replace(/\[[^\]]+\]\s*/g, "")
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .trim();

  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return `${cleaned.slice(0, maxLength - 3).trim()}...`;
}

function extractUrl(text) {
  const match = text.match(/https?:\/\/\S+/);
  return match ? match[0] : "";
}

function initialBackend() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("backend");
  if (requested && BACKENDS[requested]) {
    return requested;
  }

  const saved = window.localStorage.getItem("phase9-agent-backend");
  if (saved && BACKENDS[saved]) {
    return saved;
  }

  return window.location.port === "8090" ? "python" : "spring";
}

function setBackend(backend) {
  if (!BACKENDS[backend]) {
    return;
  }
  activeBackend = backend;
  window.localStorage.setItem("phase9-agent-backend", backend);
  renderBackend();
}

function renderBackend() {
  const backend = BACKENDS[activeBackend];

  backendStatus.textContent = backend.status;
  transportStatus.textContent = backend.transport;
  apiStatus.textContent = backend.statusApi;
  backendLabel.textContent = backend.label;
  debugTransport.textContent = backend.debugTransport;
  debugEndpoint.textContent = backend.debugEndpoint;
  debugApi.textContent = backend.debugApi;

  backendButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.backend === activeBackend);
  });

  document.querySelectorAll("[data-arc]").forEach((node) => {
    node.classList.toggle("is-current", node.dataset.arc === backend.arc);
  });
}
