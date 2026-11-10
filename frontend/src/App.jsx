import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const WELCOME = {
  role: "assistant",
  text: "Hi! I'm the Acme Widgets support bot. Ask about products, shipping, returns, or warranty — I only answer from our help docs.",
};

export default function App() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "offline", ollama: false }));
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg = Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || res.statusText || "Request failed";
        throw new Error(msg);
      }
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.reply, sources: data.sources },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Sorry — ${err.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const llmReady = health?.ollama === true;

  return (
    <div className="app">
      <header className="header">
        <Logo className="logo" />
        <div>
          <h1>Acme Widgets</h1>
          <p className="tagline">RAG support chat (local LLM + embeddings)</p>
        </div>
        <span className={`pill ${llmReady ? "ok" : "warn"}`}>
          {llmReady ? "LLM ready" : health ? "Start Ollama" : "Checking…"}
        </span>
      </header>

      <main className="chat" ref={listRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`bubble ${msg.role}${msg.error ? " error" : ""}`}>
            <span className="label">{msg.role === "user" ? "You" : "Assistant"}</span>
            <p>{msg.text}</p>
            {msg.sources?.length > 0 && (
              <details className="sources">
                <summary>Context used</summary>
                <ul>
                  {msg.sources.map((s, j) => (
                    <li key={j}>{s}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
        {loading && (
          <div className="bubble assistant loading">
            <span className="label">Assistant</span>
            <p className="dots">Thinking</p>
          </div>
        )}
      </main>

      <footer className="composer">
        <textarea
          rows={2}
          placeholder="e.g. What is the return policy for Widget Pro?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          maxLength={2000}
        />
        <button type="button" onClick={send} disabled={loading || !input.trim()}>
          Send
        </button>
      </footer>
    </div>
  );
}

function Logo({ className }) {
  return (
    <svg className={className} width="40" height="40" viewBox="0 0 40 40" aria-hidden>
      <rect x="4" y="12" width="32" height="20" rx="4" fill="#3d9eff" opacity="0.9" />
      <rect x="10" y="6" width="8" height="8" rx="2" fill="#6bb5ff" />
      <rect x="22" y="6" width="8" height="8" rx="2" fill="#6bb5ff" />
    </svg>
  );
}
