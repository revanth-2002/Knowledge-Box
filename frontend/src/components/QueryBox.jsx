import { useState } from "react";

export default function QueryBox({ onAsk, asking }) {
  const [question, setQuestion] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || asking) return;
    onAsk(trimmed);
  }

  return (
    <form className="query-card" onSubmit={handleSubmit}>
      <span className="eyebrow">Ask your inbox</span>
      <div className="query-card__row">
        <input
          className="query-card__input"
          type="text"
          placeholder="What do my notes say about…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={asking}
        />
        <button
          type="submit"
          className="btn btn--accent"
          disabled={!question.trim() || asking}
        >
          {asking ? "Thinking…" : "Ask"}
        </button>
      </div>
    </form>
  );
}
