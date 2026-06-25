const TOKEN_KEY = "medical_rag_token";
const USER_KEY = "medical_rag_user";
const API = import.meta.env.VITE_API_URL || "";

function storeSession(data) {
  if (data.access_token) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  if (data.email) {
    localStorage.setItem(USER_KEY, JSON.stringify({ id: data.user_id, email: data.email }));
  }
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function signIn(email, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  storeSession(data);
  return data;
}

export async function signUp(email, password) {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  storeSession(data);
  return data;
}

export async function signInWithGoogle() {
  throw new Error("Google sign-in not available through backend. Use email/password.");
}

export async function signOut() {
  clearSession();
}

export function onAuthChange(callback) {
  const token = localStorage.getItem(TOKEN_KEY);
  const userData = localStorage.getItem(USER_KEY);
  if (token && userData) {
    const user = JSON.parse(userData);
    callback({ user, access_token: token });
  } else {
    callback(null);
  }
  return { data: { subscription: { unsubscribe: () => {} } } };
}

export async function getSession() {
  const token = localStorage.getItem(TOKEN_KEY);
  const userData = localStorage.getItem(USER_KEY);
  if (!token || !userData) return null;
  const user = JSON.parse(userData);
  return { user, access_token: token };
}
