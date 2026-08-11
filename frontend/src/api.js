const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export { API_BASE };

export async function fetchHealth(signal) {
  const response = await fetch(`${API_BASE}/health`, { signal });
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return response.json();
}
