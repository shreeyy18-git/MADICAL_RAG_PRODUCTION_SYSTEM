// In production (Vercel), set VITE_API_URL to your Render backend URL.
// In development (Vite proxy), it falls back to relative paths.
const API = import.meta.env.VITE_API_URL || "";

export async function chat(message, conversationId, token) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function chatStream(message, conversationId, token, onToken, onMetadata, onError) {
  try {
    const res = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(trimmed.slice(6));
          if (data.type === "token") {
            onToken(data.content);
          } else if (data.type === "metadata") {
            onMetadata(data);
          } else if (data.type === "error") {
            onError(data.content);
          }
        } catch (e) {
          // skip malformed JSON
        }
      }
    }
  } catch (err) {
    onError(err.message);
  }
}

export async function health() {
  const res = await fetch(`${API}/health`);
  return res.json();
}

export async function getHistory(token) {
  const res = await fetch(`${API}/chat/history`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function getConversation(conversationId, token) {
  const res = await fetch(`/chat/history/${conversationId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export async function getProfile(token) {
  const res = await fetch(`${API}/api/profile`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch profile");
  return res.json();
}

export async function updateProfile(token, data) {
  const res = await fetch(`${API}/api/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update profile");
  return res.json();
}

export async function deleteConversation(token, conversationId) {
  const res = await fetch(`${API}/chat/history/${conversationId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
}
