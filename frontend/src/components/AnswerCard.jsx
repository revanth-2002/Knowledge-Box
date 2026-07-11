export default function AnswerCard({ result, error, asking }) {
  if (asking) {
    return (
      <div className="answer-card answer-card--loading">
        <span className="eyebrow">Answer</span>
        <p className="muted">Searching your inbox and drafting an answer…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="answer-card answer-card--error">
        <span className="eyebrow">Answer</span>
        <p className="form-error">{error}</p>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="answer-card">
      <span className="eyebrow">Answer</span>
      <p className="answer-card__text">{result.answer}</p>

      {result.sources.length > 0 && (
        <div className="answer-card__sources">
          <span className="answer-card__sources-label">Sources</span>
          <ol className="source-list">
            {result.sources.map((source, i) => (
              <li key={`${source.item_id}-${i}`} className="source-item">
                <div className="source-item__head">
                  <span className="source-item__index">[{i + 1}]</span>
                  <span className="source-item__title">{source.title}</span>
                  <span className="source-item__score">
                    {Math.round(source.similarity * 100)}% match
                  </span>
                </div>
                <p className="source-item__snippet">{source.snippet}</p>
                {source.url && (
                  <a
                    className="source-item__url"
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {source.url}
                  </a>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
