# Medical RAG — Frontend

React + Vite frontend for the Medical RAG system. Provides a responsive, mobile-friendly chat interface with streaming responses and structured markdown rendering. Deployed on Vercel (free tier).

## Stack

- **Framework**: React 19 + Vite 8
- **Routing**: React Router v7
- **Styling**: Custom CSS (no framework dependency)
- **Font**: Inter (Google Fonts)
- **Auth**: Backend HTTP auth (JWT stored in localStorage)
- **Streaming**: SSE via `ReadableStream` API
- **Build**: ~254KB JS, ~17KB CSS (gzipped: ~80KB + ~4KB)
- **Deployment**: Vercel (via `vercel.json` for SPA routing)

## Quick Start

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies API calls to `http://localhost:8000` via `vite.config.js`.

## Production Build

```bash
npm run build   # outputs to dist/
```

In production, set `VITE_API_URL` to your Render backend URL (e.g. `https://your-app.onrender.com`). The frontend automatically prepends this to all API calls. When `VITE_API_URL` is not set, it defaults to relative paths (for dev proxy).

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Landing | Welcome page with login/signup links |
| `/login` | Login | Email/password login form |
| `/register` | Register | Registration form |
| `/dashboard` | Dashboard | Live stats (total chats, questions asked), recent chats |
| `/chat` | Chat | Main chat interface with streaming responses |
| `/chat?id=xxx` | Chat | Load existing conversation by ID |
| `/history` | History | Conversation list with delete confirmation |
| `/profile` | Profile | User profile form (name, age, phone, conditions) |

## API Integration

All calls go through `src/services/api.js`. Uses `import.meta.env.VITE_API_URL` as the API base URL when set.

```javascript
// Non-streaming chat
const { answer, sources, conversation_id } = await chat("What is diabetes?", convId, token);

// Streaming chat (SSE via ReadableStream)
await chatStream("What is asthma?", convId, token,
  (token) => { /* append token to current message */ },
  (metadata) => { /* set final answer, sources, conversation_id */ },
  (error) => { /* display error message */ }
);
```

## Auth

Authentication is handled via `src/services/auth.js`:

```javascript
import { signIn, signUp, signOut, getSession } from "./services/auth";

// Register
await signUp("email@example.com", "password");

// Login
await signIn("email@example.com", "password");

// Get current session (returns null if not logged in)
const session = await getSession();
```

All auth API calls also respect `VITE_API_URL` when set.

## Design

- **Theme**: Medical teal/cyan (`#0d9488` primary)
- **Typography**: Inter font (loaded from Google Fonts)
- **Components**: Gradient pill-shaped buttons, glassmorphism navbar (`backdrop-filter: blur`), card hover animations
- **Responsive**: 3 breakpoints — tablet (1024px), phone (768px), small phone (480px)
- **Sidebar**: Slide-in drawer on mobile with backdrop blur overlay, Escape key to close
- **Chat Messages**: Rendered as markdown sections (Overview, Key Points, Details, Sources)

## Project Layout

```
src/
  pages/
    Landing.jsx         Welcome page with feature cards
    Login.jsx           Email/password login form
    Register.jsx        Registration form
    Dashboard.jsx       Stats cards + recent conversation list
    Chat.jsx            Streaming chat interface with suggestion chips
    History.jsx         Conversation history with delete button
    Profile.jsx         User profile form (name, age, conditions)
  components/
    ProtectedRoute.jsx  Auth guard + sidebar layout + mobile overlay
    Sidebar.jsx         Navigation sidebar (open prop for responsive)
    ChatBubble.jsx      Message bubble with source citations
    Loader.jsx          Animated loading indicator
  services/
    auth.js             JWT auth (register, login, logout, getSession)
    api.js              API client (chat, chatStream, history, profile, delete)
  App.jsx               Route definitions
  App.css               Complete theme + responsive styles
  main.jsx              Entry point
```

## Deployment (Vercel)

1. Import your GitHub repo in Vercel
2. Set **Root Directory** to `frontend`
3. Framework preset: **Vite**
4. Add environment variable: `VITE_API_URL` = `https://your-app.onrender.com`
5. Deploy — `vercel.json` contains SPA rewrite rules for client-side routing

The `vercel.json` file at the frontend root ensures all routes (`/chat`, `/history`, `/profile`, etc.) serve `index.html`:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```
