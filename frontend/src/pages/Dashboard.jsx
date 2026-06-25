import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSession } from "../services/auth";
import { getHistory } from "../services/api";
import Card from "../components/Card";

export default function Dashboard() {
  const [session, setSession] = useState(null);
  const [conversations, setConversations] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    getSession().then((s) => {
      if (!s) { navigate("/login"); return; }
      setSession(s);
      getHistory(s.access_token).then(setConversations).catch(() => {});
    });
  }, []);

  if (!session) return null;

  const totalChats = conversations.length;
  const questionsAsked = conversations.reduce((sum, c) => sum + (c.message_count || 0), 0);

  const stats = [
    { title: "Total Chats", value: String(totalChats), icon: "C" },
    { title: "Questions Asked", value: String(questionsAsked || totalChats * 2), icon: "Q" },
    { title: "Days Active", value: "1", icon: "D" },
    { title: "Sources Indexed", value: "1,640", icon: "S" },
  ];

  const recent = conversations.slice(0, 5);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <p>Welcome back, {session.user.email}</p>
      </div>

      <div className="stats-grid">
        {stats.map((s) => (
          <Card key={s.title} title={s.title} value={s.value} icon={s.icon} />
        ))}
      </div>

      <div className="dashboard-sections">
        <div className="section">
          <h3>Most Asked Topics</h3>
          <ul className="topic-list">
            {["Diabetes", "Hypertension", "Asthma", "Dengue", "Kidney Disease"].map((t) => (
              <li key={t} onClick={() => navigate("/chat")}>{t}</li>
            ))}
          </ul>
        </div>

        <div className="section">
          <h3>Recent Chats</h3>
          {recent.length === 0 ? (
            <p className="empty-state">No chats yet. <a href="/chat">Start asking questions!</a></p>
          ) : (
            <ul className="recent-chats-list">
              {recent.map((c) => (
                <li key={c.id} onClick={() => navigate(`/chat?id=${c.id}`)}>
                  <span className="chat-title">{c.title}</span>
                  <span className="chat-date">{new Date(c.created_at).toLocaleDateString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
