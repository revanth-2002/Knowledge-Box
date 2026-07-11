const SOURCE_LABEL = { note: "NOTE", url: "URL" };

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    " · " +
    d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export default function ItemList({ items, total, loading, error }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2 className="panel__title">Saved items</h2>
        <span className="panel__count">{total}</span>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="form-error">Could not load items: {error}</p>}

      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <p>Nothing saved yet.</p>
          <p className="muted">Add a note or paste a URL above to get started.</p>
        </div>
      )}

      <ul className="item-list">
        {items.map((item) => (
          <li key={item.id} className="item-card">
            <div className="item-card__meta">
              <span className={`tag tag--${item.source_type}`}>
                {SOURCE_LABEL[item.source_type]}
              </span>
              <span className="item-card__date">{formatDate(item.created_at)}</span>
            </div>
            <h3 className="item-card__title">{item.title}</h3>
            {item.url && (
              <a
                className="item-card__url"
                href={item.url}
                target="_blank"
                rel="noreferrer"
              >
                {item.url}
              </a>
            )}
            <p className="item-card__preview">{item.preview}</p>
            <span className="item-card__chunks">
              {item.chunk_count} chunk{item.chunk_count === 1 ? "" : "s"} indexed
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
