For the **MVP**, don't build a fancy healthcare UI. Build something that proves:

```text
Authentication ✓
RAG ✓
Chat ✓
History ✓
Dashboard ✓
```

Think **ChatGPT + Perplexity + Healthcare Theme**.

---

# Color Palette

```text
Primary: #2563EB (Blue)
Background: #F8FAFC
Cards: White
Text: #0F172A
Success: #10B981
Warning: #F59E0B
```

Why?

```text
Blue = Trust
White = Medical
Minimal = Fast Development
```

---

# Page 1: Landing Page

### Layout

```text
+------------------------------------------------+
| Logo                         Login  Get Started |
+------------------------------------------------+

            Medical AI Assistant

      Ask Medical Questions Using
      Trusted Medical Knowledge

      [Start Chatting]

--------------------------------------------------

✓ Disease Information
✓ Symptoms & Prevention
✓ Treatment Knowledge
✓ Medical Student Support

--------------------------------------------------

How It Works

Upload Knowledge
       ↓
AI Retrieval
       ↓
Accurate Answers

--------------------------------------------------

Footer
```

### Hero Section

```text
Medical AI Assistant

Understand diseases, symptoms,
prevention, treatment, and medical
concepts with AI-powered retrieval.

[Get Started]
```

### Feature Cards

```text
┌──────────────┐
│ Diseases     │
└──────────────┘

┌──────────────┐
│ Prevention   │
└──────────────┘

┌──────────────┐
│ Treatments   │
└──────────────┘

┌──────────────┐
│ Medical Edu  │
└──────────────┘
```

---

# Page 2: Login Page

Keep extremely simple.

```text
+-----------------------------+

      Medical AI

 Email

 [____________]

 Password

 [____________]

 [ Login ]

 -----------------

 [ Login with Google ]

 -----------------

 Don't have account?
 Register

+-----------------------------+
```

---

# Page 3: Dashboard

After login.

Layout:

```text
+------------------------------------------------+
| Sidebar |            Dashboard                 |
+------------------------------------------------+
```

---

## Sidebar

```text
🏠 Dashboard

💬 Chat

📜 History

👤 Profile

🚪 Logout
```

---

## Main Dashboard

### Top Cards

```text
┌──────────────┐
│ Total Chats  │
│      25      │
└──────────────┘

┌──────────────┐
│ Questions    │
│      150     │
└──────────────┘

┌──────────────┐
│ Days Active  │
│       7      │
└──────────────┘

┌──────────────┐
│ Sources Used │
│      120     │
└──────────────┘
```

---

### Most Asked Diseases

```text
Most Asked Topics

1. Diabetes
2. Hypertension
3. Asthma
4. Dengue
5. Kidney Disease
```

---

### Recent Chats

```text
Recent Chats

What is Diabetes?
Symptoms of Asthma?
What causes Hypertension?
```

Clicking opens chat.

---

# Page 4: Chat Window

This is the most important page.

---

### Layout

```text
+------------------------------------------------+
| Sidebar |              Chat                    |
+------------------------------------------------+
```

---

## Left Sidebar

```text
+ New Chat

----------------

What is Diabetes

Symptoms of Dengue

Explain Nephron

Asthma Treatment

----------------
```

Very similar to ChatGPT.

---

## Main Chat Area

```text
Medical AI Assistant

────────────────────

User:

What is Diabetes?

────────────────────

AI:

Diabetes is a chronic disease
characterized by elevated blood
glucose levels...

Sources:

• Gale Encyclopedia
• Page 210

────────────────────
```

---

## Input Box

Bottom fixed.

```text
+------------------------------------------+
| Ask a medical question...                |
+------------------------------------------+
                       [ Send ]
```

---

## Suggested Prompts

Before first message:

```text
Try asking:

• What is Diabetes?
• Symptoms of Dengue?
• Explain Nephron Function
• Asthma Prevention
```

---

# Mobile Layout

For MVP:

```text
Sidebar → Drawer

Dashboard Cards → 2 Columns

Chat → Full Width
```

No complex responsiveness.

---

# Initial MVP Navigation

```text
Landing
   │
   ▼
Login
   │
   ▼
Dashboard
   │
   ▼
Chat
```

Only 4 pages.

No:

```text
Admin Panel
Analytics
Theme Switcher
Notifications
Settings
Team Workspace
```

yet.

---

# MVP UI Components

Build only:

```text
Navbar
Sidebar
Card
Button
Input
Chat Bubble
Loader
Modal
```

That's enough.

The goal of Version 1 is not beautiful design. The goal is that a recruiter can:

1. Login
2. Ask a medical question
3. See cited answers
4. View chat history
5. See dashboard statistics

within 2 minutes of opening the app. That's what demonstrates the backend architecture you just built.
