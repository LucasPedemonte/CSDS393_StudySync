import { useState, useEffect } from "react";

const API = "http://127.0.0.1:8000";

export default function ResourceLibrary() {
  const [resources, setResources] = useState([]);
  const [form, setForm] = useState({ title: "", url: "", description: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchResources = () => {
    fetch(`${API}/resources`)
      .then((r) => r.json())
      .then(setResources)
      .catch(() => setError("Could not load resources."));
  };

  useEffect(() => { fetchResources(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    const res = await fetch(`${API}/resources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setSuccess("Resource submitted!");
      setForm({ title: "", url: "", description: "" });
      fetchResources();
    } else {
      setError("Failed to submit resource.");
    }
  };

  const handleVote = async (id) => {
    const res = await fetch(`${API}/resources/${id}/vote?user_id=1&vote=1`, { method: "POST" });
    if (res.ok) {
      fetchResources();
    } else {
      const data = await res.json();
      setError(data.detail || "Could not vote.");
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: "40px auto", fontFamily: "'DM Sans', sans-serif", color: "#f0f4ff", padding: "0 20px" }}>
      <h1 style={{ color: "#2dd4bf" }}>📚 Resource Library</h1>

      <form onSubmit={handleSubmit} style={{ marginBottom: 32, background: "#161f3a", padding: 20, borderRadius: 12, border: "1px solid rgba(45,212,191,0.15)" }}>
        <h2 style={{ marginTop: 0, color: "#f0f4ff" }}>Share a Resource</h2>
        <input required placeholder="Title" value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ display: "block", width: "100%", marginBottom: 8, padding: 8, boxSizing: "border-box", background: "#0f1729", border: "1px solid #2dd4bf44", borderRadius: 6, color: "#f0f4ff" }} />
        <input required placeholder="URL (https://...)" value={form.url}
          onChange={(e) => setForm({ ...form, url: e.target.value })}
          style={{ display: "block", width: "100%", marginBottom: 8, padding: 8, boxSizing: "border-box", background: "#0f1729", border: "1px solid #2dd4bf44", borderRadius: 6, color: "#f0f4ff" }} />
        <textarea placeholder="Description (optional)" value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ display: "block", width: "100%", marginBottom: 8, padding: 8, boxSizing: "border-box", background: "#0f1729", border: "1px solid #2dd4bf44", borderRadius: 6, color: "#f0f4ff" }} />
        <button type="submit" style={{ padding: "8px 20px", background: "#2dd4bf", color: "#0f1729", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: "bold" }}>
          Submit
        </button>
        {success && <p style={{ color: "#2dd4bf" }}>{success}</p>}
        {error && <p style={{ color: "#f87171" }}>{error}</p>}
      </form>

      <h2>Top Resources</h2>
      {resources.length === 0 && <p style={{ color: "#7b8aad" }}>No resources yet. Be the first to share one!</p>}
      {resources.map((r) => (
        <div key={r.id} style={{ border: "1px solid rgba(45,212,191,0.15)", borderRadius: 12, padding: 16, marginBottom: 12, display: "flex", gap: 16, alignItems: "flex-start", background: "#161f3a" }}>
          <div style={{ textAlign: "center", minWidth: 48 }}>
            <button onClick={() => handleVote(r.id)}
              style={{ background: "none", border: "1px solid #2dd4bf", borderRadius: 4, cursor: "pointer", fontSize: 20, padding: "2px 8px", color: "#2dd4bf" }}>
              ▲
            </button>
            <div style={{ fontWeight: "bold", fontSize: 18, color: "#2dd4bf" }}>{r.vote_score}</div>
          </div>
          <div>
            <a href={r.url} target="_blank" rel="noreferrer" style={{ fontSize: 18, fontWeight: "bold", color: "#2dd4bf" }}>
              {r.title}
            </a>
            {r.is_verified && <span style={{ marginLeft: 8, background: "#064e3b", color: "#2dd4bf", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>✓ TA Verified</span>}
            {r.description && <p style={{ margin: "6px 0 0", color: "#7b8aad" }}>{r.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
