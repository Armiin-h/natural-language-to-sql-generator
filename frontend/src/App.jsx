import { useEffect, useState } from "react";
import { API_BASE, fetchHealth } from "./api";
import "./App.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const data = await fetchHealth(controller.signal);
        if (!cancelled) {
          setHealth(data);
          setHealthError(null);
        }
      } catch (err) {
        if (!cancelled && err?.name !== "AbortError") {
          setHealth(null);
          setHealthError(err instanceof Error ? err.message : "Could not reach API");
        }
      }
    }

    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="page">
      <header className="hero">
        <p className="brand">AskSQL</p>
        <h1>Ask your database in English</h1>
        <p className="lede">
          Scaffold is up. Query generation and results land in upcoming days.
        </p>
      </header>

      <section className="status" aria-live="polite">
        <h2>API status</h2>
        {healthError && (
          <p className="status-error">
            Offline — {healthError}. Start the API on {API_BASE}.
          </p>
        )}
        {health && !healthError && (
          <dl className="status-grid">
            <div>
              <dt>Status</dt>
              <dd>{health.status}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{health.ollama_model}</dd>
            </div>
            <div>
              <dt>Database</dt>
              <dd>{health.database}</dd>
            </div>
            <div>
              <dt>Row limit</dt>
              <dd>{health.sql_row_limit}</dd>
            </div>
          </dl>
        )}
        {!health && !healthError && <p className="status-pending">Checking API…</p>}
      </section>
    </div>
  );
}
