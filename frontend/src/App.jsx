import { useItems } from "./hooks/useItems.js";
import { useQuery } from "./hooks/useQuery.js";
import NoteInput from "./components/NoteInput.jsx";
import ItemList from "./components/ItemList.jsx";
import QueryBox from "./components/QueryBox.jsx";
import AnswerCard from "./components/AnswerCard.jsx";

export default function App() {
  const { items, total, loading, error, refresh } = useItems();
  const { result, asking, error: queryError, ask } = useQuery();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__mark">KI</span>
          <div>
            <h1 className="app-header__title">Knowledge Inbox</h1>
            <p className="app-header__subtitle">
              Drop in notes and links. Ask questions across all of it.
            </p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="app-main__left">
          <NoteInput onSaved={refresh} />
          <ItemList items={items} total={total} loading={loading} error={error} />
        </div>

        <div className="app-main__right">
          <QueryBox onAsk={ask} asking={asking} />
          <AnswerCard result={result} error={queryError} asking={asking} />
        </div>
      </main>
    </div>
  );
}
