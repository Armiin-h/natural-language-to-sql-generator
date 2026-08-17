import { useEffect, useRef, useState } from "react";
import { API_BASE, fetchExamples, fetchHealth, postQuery } from "./api";
import "./App.css";

const FALLBACK_EXAMPLES = [
  "Show the top 5 products by sales",
  "How many customers live in the USA?",
  "List products in the Electronics category",
  "How many orders were cancelled?",
];

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES);
  const [question, setQuestion] = useState(FALLBACK_EXAMPLES[0]);
  const [result, setResult] = useState(null);
  const [queryError, setQueryError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(null);

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

    async function loadExamples() {
      try {
        const data = await fetchExamples(controller.signal);
        if (!cancelled && Array.isArray(data.examples) && data.examples.length) {
          setExamples(data.examples);
        }
      } catch {
        // Keep fallback examples.
      }
    }

    checkHealth();
    loadExamples();
    const timer = setInterval(checkHealth, 30000);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  async function handleAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setQueryError(null);
    setResult(null);

    try {
      const data = await postQuery(trimmed, { includeSteps: false, signal: controller.signal });
      setResult(data);
      if (!data.success) {
        setQueryError(data.error || "Query did not succeed");
      }
    } catch (err) {
      if (err?.name !== "AbortError") {
        setQueryError(err instanceof Error ? err.message : "Query failed");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <p className="brand">AskSQL</p>
        <h1>Ask your database in English</h1>
        <p className="lede">
          A local SQL agent turns your question into a safe SELECT, runs it on the
          sample ecommerce database, and shows the results.
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
              <dt>Ollama</dt>
              <dd>{health.ollama_reachable ? "up" : "down"}</dd>
            </div>
            <div>
              <dt>Tables</dt>
              <dd>{health.tables_ready ? "ready" : "missing"}</dd>
            </div>
          </dl>
        )}
        {!health && !healthError && <p className="status-pending">Checking API…</p>}
      </section>

      <section className="ask">
        <h2>Ask a question</h2>
        <div className="examples" aria-label="Example questions">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              className="example"
              onClick={() => setQuestion(example)}
              disabled={isLoading}
            >
              {example}
            </button>
          ))}
        </div>

        <form className="ask-form" onSubmit={handleAsk}>
          <label className="sr-only" htmlFor="question">
            Question
          </label>
          <textarea
            id="question"
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. Show the top 5 products by sales"
            disabled={isLoading}
          />
          <div className="ask-actions">
            <button type="submit" disabled={isLoading || !question.trim()}>
              {isLoading ? "Running…" : "Generate SQL"}
            </button>
          </div>
        </form>

        {queryError && <p className="status-error">{queryError}</p>}
      </section>

      {result && (
        <section className="results" aria-live="polite">
          <h2>Result</h2>
          <dl className="status-grid">
            <div>
              <dt>Success</dt>
              <dd>{result.success ? "yes" : "no"}</dd>
            </div>
            <div>
              <dt>Attempts</dt>
              <dd>{result.attempts}</dd>
            </div>
            <div>
              <dt>Rows</dt>
              <dd>{result.row_count}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{result.model}</dd>
            </div>
          </dl>

          {result.final_sql && (
            <div className="sql-panel">
              <h3>SQL</h3>
              <pre>
                <code>{result.final_sql}</code>
              </pre>
            </div>
          )}

          {result.answer && (
            <div className="answer-panel">
              <h3>Answer</h3>
              <p>{result.answer}</p>
            </div>
          )}

          {result.columns?.length > 0 && (
            <div className="table-wrap">
              <h3>Rows</h3>
              <table>
                <thead>
                  <tr>
                    {result.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, index) => (
                    <tr key={`row-${index}`}>
                      {row.map((cell, cellIndex) => (
                        <td key={`cell-${index}-${cellIndex}`}>{formatCell(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.truncated && <p className="status-pending">Result truncated by row limit.</p>}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function formatCell(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
