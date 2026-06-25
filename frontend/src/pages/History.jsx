import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSession } from "../services/auth";
import { getHistory, deleteConversation } from "../services/api";

export default function HistoryPage() {
  const [session, setSession] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getSession().then((s) => {
      if (!s) {
        navigate("/login");
      } else {
        setSession(s);
        fetchHistory(s.access_token);
      }
    });
  }, [navigate]);

  const fetchHistory = async (token) => {
    try {
      const data = await getHistory(token);
      setConversations(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const openConversation = (id) => {
    navigate(`/chat?id=${id}`);
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(session.access_token, id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      alert("Failed to delete: " + err.message);
    }
  };

  if (!session) return null;

  return (
    <div className="history-page">
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: "2rem"
      }}>
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: 700, letterSpacing: "-0.02em" }}>Your Conversations</h2>
          <p style={{ color: "var(--text-light)", fontSize: "14px", marginTop: "4px" }}>
            {conversations.length} saved conversations
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/chat")}>
          New Chat
        </button>
      </div>

      {loading ? (
        <div className="loader" style={{ justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner"></div>
          <p>Loading history...</p>
        </div>
      ) : conversations.length === 0 ? (
        <div style={{ textAlign: "center", padding: "80px 24px", color: "var(--text-light)" }}>
          <div className="welcome-icon" style={{ margin: "0 auto 20px", width: "64px", height: "64px", fontSize: "28px", borderRadius: "16px" }}>H</div>
          <p style={{ fontSize: "16px", marginBottom: "16px" }}>No past conversations found.</p>
          <button className="btn btn-primary" onClick={() => navigate("/chat")}>Start a Chat</button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="history-card"
              onClick={() => openConversation(conv.id)}
              style={{
                padding: "18px 20px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <h3 style={{
                  margin: "0 0 6px 0", fontSize: "15px", fontWeight: 600,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                }}>{conv.title}</h3>
                <small style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                  {new Date(conv.created_at).toLocaleString()}
                  {conv.message_count > 0 && ` · ${conv.message_count} messages`}
                </small>
              </div>
              <button
                className="btn-danger"
                onClick={(e) => handleDelete(e, conv.id)}
                title="Delete conversation"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
