import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { getSession } from "../services/auth";
import { chat, getConversation, chatStream } from "../services/api";
import ChatBubble from "../components/ChatBubble";
import Loader from "../components/Loader";

const suggestions = [
  "What is Diabetes?",
  "Symptoms of Dengue?",
  "Explain Nephron Function",
  "Asthma Prevention",
];

export default function ChatPage() {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const bottomRef = useRef(null);
  const streamingRef = useRef(false);

  useEffect(() => {
    getSession().then(async (s) => {
      if (!s) {
        navigate("/login");
      } else {
        setSession(s);
        const id = searchParams.get("id");
        if (id) {
          setConvId(id);
          try {
            const data = await getConversation(id, s.access_token);
            setMessages(data);
          } catch (err) {
            console.error("Failed to load conversation", err);
          }
        }
      }
    });
  }, [navigate, searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (msg) => {
    const text = msg || input;
    if (!text.trim() || loading || streamingRef.current) return;
    setInput("");

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const assistantMsg = { role: "assistant", content: "", sources: [] };
    setMessages((prev) => [...prev, assistantMsg]);

    streamingRef.current = true;
    let accumulated = "";

    chatStream(
      text,
      convId,
      session.access_token,
      (token) => {
        accumulated += token;
        setMessages((prev) => {
          const updated = [...prev];
          const last = { ...updated[updated.length - 1], content: accumulated };
          updated[updated.length - 1] = last;
          return updated;
        });
      },
      (metadata) => {
        setConvId(metadata.conversation_id);
        setMessages((prev) => {
          const updated = [...prev];
          const last = {
            ...updated[updated.length - 1],
            content: metadata.answer || accumulated,
            sources: metadata.sources || [],
            flagged: metadata.flagged_emergency,
          };
          updated[updated.length - 1] = last;
          return updated;
        });
        setLoading(false);
        streamingRef.current = false;
      },
      (error) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: `Error: ${error}`,
          };
          return updated;
        });
        setLoading(false);
        streamingRef.current = false;
      }
    );
  };

  if (!session) return null;

  return (
    <div className="chat-page">
      <div className="chat-messages" id="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="chat-welcome">
            <div style={{ display: "flex", justifyContent: "flex-end", padding: "10px" }}>
              <Link to="/history" style={{ color: "var(--primary)", textDecoration: "none", fontSize: "14px", fontWeight: 500 }}>
                View Past Chats &rarr;
              </Link>
            </div>
            <div className="welcome-icon">+</div>
            <h2>Medical AI Assistant</h2>
            <p>Ask any medical question using trusted knowledge sources</p>
            <div className="suggestions">
              {suggestions.map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => handleSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <ChatBubble key={i} role={m.role} content={m.content} sources={m.sources} />
        ))}
        {loading && messages.length > 0 && messages[messages.length - 1].content === "" && (
          <Loader />
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask a medical question..."
          disabled={loading}
        />
        <button className="btn btn-primary" onClick={() => handleSend()} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
