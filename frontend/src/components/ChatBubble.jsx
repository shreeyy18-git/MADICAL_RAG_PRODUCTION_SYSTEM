function renderStructured(text) {
  if (!text) return "";
  let html = text
    .replace(/^## (.+)$/gm, '<h3 class="section-heading">$1</h3>')
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[(\d+(?:,\s*\d+)*)\]/g, '<sup class="citation">[$1]</sup>');
  html = html.replace(/(<li>.*?<\/li>\n?)+/g, '<ul class="key-points">$&</ul>');
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  return html;
}

export default function ChatBubble({ role, content, sources }) {
  const isUser = role === "user";
  return (
    <div className={`chat-bubble ${isUser ? "user" : "assistant"}`}>
      <div className="chat-avatar">{isUser ? "U" : "AI"}</div>
      <div className="chat-content">
        {isUser ? (
          <p>{content}</p>
        ) : (
          <div className="structured-answer" dangerouslySetInnerHTML={{ __html: renderStructured(content) }} />
        )}
        {sources && sources.length > 0 && (
          <details className="sources">
            <summary>Sources ({sources.length})</summary>
            {sources.map((s, i) => (
              <div key={i} className="source-item">
                <span className="source-doc">{s.document_name}</span>
                <span className="source-score">{(s.score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </details>
        )}
      </div>
    </div>
  );
}
