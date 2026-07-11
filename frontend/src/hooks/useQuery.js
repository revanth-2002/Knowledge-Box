import { useCallback, useState } from "react";
import { askQuestion } from "../api/client.js";

export function useQuery() {
  const [result, setResult] = useState(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(null);

  const ask = useCallback(async (question) => {
    setAsking(true);
    setError(null);
    try {
      const data = await askQuestion(question);
      setResult(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setAsking(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, asking, error, ask, reset };
}
