import { useState } from "react";
import { ingestContent } from "../api/client.js";

const URL_PATTERN = /^https?:\/\//i;

export default function NoteInput({ onSaved }) {
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [justSaved, setJustSaved] = useState(false);

  const trimmed = content.trim();
  const detectedType = URL_PATTERN.test(trimmed) ? "url" : "note";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!trimmed || saving) return;

    setSaving(true);
    setError(null);
    setJustSaved(false);
    try {
      await ingestContent({ sourceType: detectedType, content: trimmed });
      setContent("");
      setJustSaved(true);
      onSaved?.();
      setTimeout(() => setJustSaved(false), 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="capture-card" onSubmit={handleSubmit}>
      <div className="capture-card__header">
        <span className="eyebrow">Add to inbox</span>
        <span className={`type-pill type-pill--${detectedType}`}>
          {detectedType === "url" ? "URL detected" : "plain note"}
        </span>
      </div>

      <textarea
        className="capture-card__textarea"
        placeholder="Paste a note, or drop a URL to fetch its content..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={4}
        disabled={saving}
      />

      <div className="capture-card__footer">
        <span className="capture-card__hint">
          {detectedType === "url"
            ? "We'll fetch and extract the page content server-side."
            : "Saved as-is, then chunked and embedded for search."}
        </span>
        <button type="submit" className="btn btn--primary" disabled={!trimmed || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}
      {justSaved && <p className="form-success">Saved to your inbox.</p>}
    </form>
  );
}
