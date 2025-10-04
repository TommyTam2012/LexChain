"use client";
import { useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.trim() !== ""
    ? process.env.NEXT_PUBLIC_API_BASE
    : "/lexapi";

export default function Page() {
  const [health, setHealth] = useState(null);
  const [version, setVersion] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);

  async function call(endpoint, setter) {
    try {
      setBusy(true);
      setError("");
      const res = await fetch(`${API_BASE}${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setter(await res.json());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (!q.trim()) return;
    try {
      setBusy(true);
      setError("");
      const res = await fetch(`${API_BASE}/cases/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResults(await res.json());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h1>LexChain — Demo UI</h1>
      <p style={{ color: "#555" }}>Ping backend and search stub cases.</p>

      <div style={{ display: "flex", gap: 12, margin: "16px 0" }}>
        <button onClick={() => call("/health", setHealth)} disabled={busy}>Check Health</button>
        <button onClick={() => call("/version", setVersion)} disabled={busy}>Get Version</button>
      </div>

      <div style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search cases (e.g., contract, privacy, appeal)"
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={search} disabled={busy || !q.trim()}>Search</button>
      </div>

      {busy && <p>⏳ contacting backend…</p>}
      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      <section style={{ marginTop: 20 }}>
        <h3>Health</h3>
        <pre style={{ background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </section>

      <section style={{ marginTop: 20 }}>
        <h3>Version</h3>
        <pre style={{ background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
{JSON.stringify(version, null, 2)}
        </pre>
      </section>

      <section style={{ marginTop: 20 }}>
        <h3>Search Results</h3>
        <pre style={{ background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
{JSON.stringify(results, null, 2)}
        </pre>

        {results?.items?.length > 0 && (
          <ul style={{ marginTop: 12 }}>
            {results.items.map((c) => (
              <li key={c.id} style={{ marginBottom: 10 }}>
                <strong>{c.title}</strong> — {c.court} ({c.date})
                <div style={{ color: "#555" }}>{c.summary}</div>
                {c.citations?.length ? (
                  <div style={{ fontSize: 12, color: "#777" }}>
                    cites: {c.citations.join(", ")}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
