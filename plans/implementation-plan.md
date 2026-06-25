# Medical RAG MVP (Production-Style, Free Tier)

## Objective

Build an AI-powered Medical RAG Assistant that can answer health, disease, symptom, prevention, treatment, and medical education questions using a trusted medical knowledge base.

Target users:

* General users / patients
* Medical students

---

# Core Features

## User Authentication

* Email/Password Login
* Google Login
* Supabase Authentication
* JWT-based session management

---

## Medical Knowledge Base

Primary source:

* The Gale Encyclopedia of Medicine

Knowledge ingestion pipeline:

* PDF Upload
* Text Extraction
* Cleaning
* Chunking
* Embedding Generation
* Qdrant Storage

---

## Medical Question Answering

User can ask:

* Disease-related questions
* Symptom-related questions
* Prevention-related questions
* Treatment-related questions
* Drug-related questions
* Medical concept questions

Examples:

* What is Diabetes?
* What causes Asthma?
* Symptoms of Dengue?
* How is Hypertension treated?
* Explain Nephron Function.

---

## Retrieval-Augmented Generation (RAG)

Pipeline:

User Query

↓

Query Embedding

↓

Qdrant Vector Search

↓

Relevant Chunks

↓

Groq LLM

↓

Answer Generation

↓

Source Citations

---

## Hybrid Search

Combine:

* Vector Search (Qdrant)
* BM25 Search

Benefits:

* Better keyword matching
* Better semantic retrieval

---

## Query Rewriting

Convert user queries into optimized medical search queries.

Example:

medicine for sugar

↓

What medications are commonly prescribed for Type 2 Diabetes?

---

## Reranking

Use:

cross-encoder/ms-marco-MiniLM-L6-v2

Pipeline:

Retrieved Chunks

↓

Reranker

↓

Best Chunks

↓

LLM

---

## Source Citations

Every answer should include:

* Source Book
* Page Information (if available)
* Retrieved Context

---

## Conversation History

Store:

* User Questions
* Assistant Responses
* Timestamps

Using Supabase.

---

## Long-Term Memory

Store important user facts.

Examples:

* User has Type 2 Diabetes
* User allergic to Penicillin

Storage:

* Supabase
* Qdrant Memory Collection

---

## Rate Limiting

Use Upstash Redis.

Example:

* 10 requests/minute/user

---

## Response Caching

Cache frequently asked questions.

Examples:

* What is Diabetes?
* Symptoms of Asthma?

Using Upstash Redis.

---

## Observability

Use Langfuse Cloud.

Track:

* User Query
* Retrieval Results
* Prompt
* LLM Response
* Latency
* Token Usage

---

# Technology Stack

Backend

* FastAPI
* LangChain
* LangGraph
* LiteLLM

LLM

* Groq (Primary)
* Gemini Flash (Fallback)

Embeddings

* BAAI/bge-small-en-v1.5

Vector Database

* Qdrant Cloud

Authentication

* Supabase Auth

Database

* Supabase PostgreSQL

Cache

* Upstash Redis

Monitoring

* Langfuse Cloud

Deployment

* Render (Backend)
* Vercel (Frontend)

---

# User Request Flow

User Question

↓

Authentication Check

↓

Rate Limit Check

↓

Query Rewrite

↓

Memory Retrieval

↓

Hybrid Search

(BM25 + Qdrant)

↓

Reranker

↓

Context Assembly

↓

Groq LLM

↓

Medical Safety Prompt

↓

Response Generation

↓

Store Chat History

↓

Update Memory

↓

Langfuse Trace

↓

Return Response

---

# Safety Rules

The assistant must:

* Never claim to be a doctor.
* Never provide emergency diagnosis.
* Never replace professional medical advice.
* Always encourage consultation with qualified healthcare professionals.
* Display disclaimer for high-risk medical situations.

Example:

"If you are experiencing severe chest pain, difficulty breathing, stroke symptoms, or any medical emergency, seek immediate medical attention."

---

# Deliverable

A deployed Medical RAG web application where users can:

* Sign up/Login
* Upload medical knowledge PDFs (admin)
* Ask medical questions
* Receive cited answers
* View chat history
* Benefit from memory-aware conversations
* Use the system on desktop and mobile

Deployment:

* Backend: Render
* Frontend: Vercel
* Qdrant Cloud
* Supabase
* Upstash Redis
* Langfuse Cloud
