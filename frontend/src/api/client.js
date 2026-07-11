const BASE_URL = "/api";

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    // no JSON body
  }

  if (!response.ok) {
    const errorInfo = body?.error || body?.detail;
    const message =
      (typeof errorInfo === "string" && errorInfo) ||
      errorInfo?.message ||
      (Array.isArray(body?.detail) && body.detail[0]?.msg) ||
      `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, errorInfo?.code);
  }

  return body;
}

export function ingestContent({ sourceType, content }) {
  return request("/ingest", {
    method: "POST",
    body: JSON.stringify({ source_type: sourceType, content }),
  });
}

export function listItems() {
  return request("/items");
}

export function askQuestion(question) {
  return request("/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export { ApiError };
