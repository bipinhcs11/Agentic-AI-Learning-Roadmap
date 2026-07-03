import { useEffect, useMemo, useRef, useState } from "react";
import { validateA2uiPayload, trustedCatalogLabel } from "./a2uiCatalog";
import { A2uiRenderer } from "./a2uiRenderer";
import "./styles.css";

const FIXTURE_PATH = "/a2ui-projection-fixture.json";
const STREAM_URL = "http://127.0.0.1:8091/ag-ui/runs/benefits-projection";
const AG_UI_EVENTS = [
  "RUN_STARTED",
  "STEP_STARTED",
  "STEP_FINISHED",
  "TEXT_MESSAGE_START",
  "TEXT_MESSAGE_CONTENT",
  "TEXT_MESSAGE_END",
  "TOOL_CALL_START",
  "TOOL_CALL_ARGS",
  "TOOL_CALL_END",
  "STATE_SNAPSHOT",
  "RUN_FINISHED",
  "RUN_ERROR",
];

export default function App() {
  const [payload, setPayload] = useState(null);
  const [loadState, setLoadState] = useState("loading");
  const [error, setError] = useState("");
  const [mode, setMode] = useState("fixture");
  const [streamState, setStreamState] = useState("idle");
  const [streamEvents, setStreamEvents] = useState([]);
  const [streamedText, setStreamedText] = useState("");
  const streamRef = useRef(null);

  async function loadFixture() {
    closeStream();
    setMode("fixture");
    setStreamState("idle");
    setStreamEvents([]);
    setStreamedText("");
    setLoadState("loading");
    setError("");

    try {
      const response = await fetch(FIXTURE_PATH, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Fixture request failed with ${response.status}`);
      }
      setPayload(await response.json());
      setLoadState("ready");
    } catch (fixtureError) {
      setError(fixtureError.message);
      setLoadState("error");
    }
  }

  function startStream() {
    closeStream();
    setMode("stream");
    setLoadState("loading");
    setStreamState("connecting");
    setStreamEvents([]);
    setStreamedText("");
    setError("");

    const source = new EventSource(STREAM_URL);
    streamRef.current = source;

    AG_UI_EVENTS.forEach((eventType) => {
      source.addEventListener(eventType, (message) => handleStreamEvent(JSON.parse(message.data), source));
    });

    source.onerror = () => {
      setStreamState("error");
      setLoadState("error");
      setError("Stream server unavailable at 127.0.0.1:8091");
      closeStream();
    };
  }

  function handleStreamEvent(event, source) {
    setStreamEvents((items) => [...items, event].slice(-8));

    if (event.type === "RUN_STARTED") {
      setStreamState("running");
    }

    if (event.type === "TEXT_MESSAGE_CONTENT") {
      setStreamedText((current) => `${current}${event.delta}`);
    }

    if (event.type === "STATE_SNAPSHOT") {
      setPayload(event.snapshot.a2uiPayload);
      setLoadState("ready");
    }

    if (event.type === "RUN_FINISHED") {
      setStreamState("finished");
      source.close();
      streamRef.current = null;
    }

    if (event.type === "RUN_ERROR") {
      setStreamState("error");
      setLoadState("error");
      setError(event.message ?? "Stream failed");
      source.close();
      streamRef.current = null;
    }
  }

  function closeStream() {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  }

  useEffect(() => {
    loadFixture();

    return () => closeStream();
  }, []);

  const clientValidation = useMemo(() => validateA2uiPayload(payload), [payload]);
  const serverValidation = payload?.data?.validation;
  const canRender = loadState === "ready" && clientValidation.valid && serverValidation?.valid;

  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="summary-panel">
          <div>
            <p className="eyebrow">{mode === "stream" ? "Rung 01D" : "Rung 01C"}</p>
            <h1>{mode === "stream" ? "AG-UI Stream" : "React A2UI Renderer"}</h1>
          </div>
          <dl className="meta-grid">
            <MetaItem label="Schema" value={payload?.data?.schemaVersion ?? "pending"} />
            <MetaItem label="MIME" value={payload?.metadata?.mimeType ?? "pending"} />
            <MetaItem label="Catalog" value={trustedCatalogLabel(payload)} />
            <MetaItem label="Server validation" value={serverValidation?.valid ? "valid" : "pending"} />
            <MetaItem label="Stream" value={streamState} />
          </dl>
          <div className="actions">
            <button type="button" onClick={startStream}>
              Start stream
            </button>
            <button type="button" className="button-secondary" onClick={loadFixture}>
              Reload fixture
            </button>
          </div>
          {streamedText && <p className="stream-text">{streamedText}</p>}
          {streamEvents.length > 0 && (
            <ol className="event-list" aria-label="AG-UI events">
              {streamEvents.map((event, index) => (
                <li key={`${event.type}-${event.timestamp}-${index}`}>{event.type}</li>
              ))}
            </ol>
          )}
        </div>

        <div className="render-panel">
          {loadState === "loading" && <StatusPanel title="Loading fixture" tone="neutral" />}
          {loadState === "error" && <StatusPanel title={error} tone="danger" />}
          {loadState === "ready" && !canRender && (
            <StatusPanel title="Payload blocked by catalog validation" tone="danger" errors={clientValidation.errors} />
          )}
          {canRender && <A2uiRenderer component={payload.data.root} />}
        </div>
      </section>
    </main>
  );
}

function MetaItem({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function StatusPanel({ title, tone, errors = [] }) {
  return (
    <div className={`status status--${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <h2>{title}</h2>
      {errors.length > 0 && (
        <ul>
          {errors.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
