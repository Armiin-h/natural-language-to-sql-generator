const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export { API_BASE };

export async function fetchHealth(signal) {
  const response = await fetch(`${API_BASE}/health`, { signal });
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return response.json();
}

export async function fetchExamples(signal) {
  const response = await fetch(`${API_BASE}/examples`, { signal });
  if (!response.ok) {
    throw new Error(`Examples failed (${response.status})`);
  }
  return response.json();
}

export async function postQuery(question, { includeSteps = false, signal } = {}) {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, include_steps: includeSteps }),
    signal,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : `Query failed (${response.status})`;
    throw new Error(message);
  }

  return payload;
}
