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

  async function call(endpoint, setter) {
    try {
      setBusy(true);
      setError("");
      const res = await fetch(`${API_BASE}${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setter(json);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h1>LexChain — Frontend Stub (App Router)</h1>
      <p style={{ color: "#555" }}>
        Tiny UI to ping the FastAPI backend via <code>/lexapi</code> rewrite.
      </p>

      <div style={{ display: "flex", gap: 12, margin: "16px 0" }}>
        <button onClick={() => call("/health", setHealth)} disabled={busy}>
          Check Health
        </button>
        <button onClick={() => call("/version", setVersion)} disabled={busy}>
          Get Version
        </button>
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

      <hr style={{ margin: "24px 0" }} />
      <p style={{ fontSize: 12, color: "#777" }}>
        Backend expected at <code>http://localhost:8000</code>. Frontend rewrites{" "}
        <code>/lexapi/*</code> → backend.
      </p>
    </main>
  );
}
