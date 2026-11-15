const API_BASE_URL = "http://localhost:8000/api";

async function getJson(path: string) {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export async function fetchModes() {
  return getJson("/modes");
}

export async function fetchUserGraph(userId: string = "local") {
  return getJson(`/graph/${userId}`);
}

export async function fetchHistory(userId: string = "local") {
  return getJson(`/history/${userId}`);
}

export async function sendChatMessage(userId: string, message: string, mode: string) {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message, mode }),
  });
  if (!res.ok) throw new Error(`POST /chat failed: ${res.status}`);
  return res.json();
}