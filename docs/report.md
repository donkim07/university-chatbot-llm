# Technical Report: Self-Hosted LLM University Student Support Assistant

## 1. Introduction
This report describes the implementation of a full-stack, self-hosted Large Language Model (LLM) pipeline configured as a **University Student Support Assistant**. The goal of the system is to assist students in finding accurate and timely information on course registration, examination rules, library services, ICT support, hostel application, fee payment, academic calendar, and student conduct.

Rather than relying on generic model intelligence, this system leverages a self-hosted Small Language Model (SLM) integrated with a local Retrieval-Augmented Generation (RAG) database, providing grounded answers matching the university's specific regulations and dates.

---

## 2. System Use Case
The system serves as a primary support layer for university administration. It answers questions like:
- "When is the deadline to register for classes?" (Course Registration)
- "What happens if I miss an exam due to illness?" (Examination Rules)
- "How many books can I borrow from the library?" (Library Services)
- "How do I reset my portal password?" (ICT Support)
- "What are the hostel accommodation fees?" (Hostel Application)
- "Is there an instalment plan for tuition?" (Fee Payment)
- "What is the dress code and rules on student IDs?" (Student Conduct)

---

## 3. Tools and Technologies Used
- **Backend Framework**: Python 3.10+ / FastAPI & Uvicorn for asynchronous, fast, and scalable API routing.
- **Frontend Framework**: Streamlit (Python) for a responsive, interactive, and premium chat dashboard.
- **LLM Serving Engine**: Ollama (Local Server).
- **LLM Model**: `llama3.2:1b` (a lightweight 1.3B parameter model suited for low-latency local execution).
- **RAG Component**: Standard Library Python JSON-based keyword matcher (using intersection Jaccard similarity over tokenized, cleaned queries).
- **Configuration & Logging**: Pydantic Settings for configuration; standard Python logging module for structured audits.

---

## 4. System Architecture

```
User <---> Streamlit UI (app.py:8501) <---> FastAPI Backend (main.py:8000) <---> Ollama Local API (11434)
                                                    |
                                            +-------+-------+
                                            |               |
                                     faq_data.json       app.log
```

1. **User Request**: The student asks a question via the Streamlit UI.
2. **Retrieve Context (RAG)**: The FastAPI backend cleans the student's question, performs word-overlap scoring against the `faq_data.json` database, and retrieves the most similar FAQ pair if the similarity exceeds `0.15`.
3. **LLM Invocation**: The backend constructs a system prompt directing the LLM to use the retrieved context as the primary source of truth. It sends this combined prompt to the local Ollama instance running `llama3.2:1b`.
4. **Logging & Response**: The interaction (question, generated answer, category, timestamp, RAG utilization status) is logged to `backend/logs/app.log`. The answer is returned to the Streamlit UI.
5. **Feedback Loop**: The user can rate the response quality (Good / Average / Poor) in the UI. Feedback is recorded instantly in `backend/logs/feedback.json`.

---

## 5. Implementation Steps
1. **Repository Setup**: Initialized directory structure matching the recommended layout.
2. **Environment Configuration**: Set up a virtual environment `.venv`, configured dependencies inside `requirements.txt`, and verified the Python 3.10+ installation.
3. **Ollama Integration**: Pulled the model `llama3.2:1b` locally and validated connection via health checks.
4. **Backend Implementation**: Created configuration files, RAG retrieval engine, FastAPI routes (`/health` and `/ask`), logging pipelines, and error boundaries.
5. **Frontend Development**: Created a high-fidelity Streamlit user interface featuring glassmorphic sidebar widgets, status panels, reactive chat layouts, loading spinners, and response evaluation buttons.
6. **Automation & Testing**: Programmed `tests/test_api.py` to trigger health checks and chat queries automatically, validating API responses.

---

## 6. Testing and Results
Testing is automated using `tests/test_api.py`.
- **Health Verification**: Ensures backend is active and the connection to the Ollama server is intact.
- **Standard Queries**: Validates correct answers and shows whether RAG context was correctly retrieved and appended to the prompt.
- **Validation**: Sends invalid inputs (empty queries) to verify a `400 Bad Request` is properly raised.
- **Connection Failure Handling**: Simulates frontend resilience when the backend is offline.

---

## 7. Challenges Encountered
1. **Ollama Connection Timeouts**: Initial execution of local models may cause cold start lag. This was solved by configuring generous timeouts (30s) in HTTPX clients.
2. **Prompt Hallucination**: Without RAG, `llama3.2:1b` would invent fictional university dates and room numbers. Implementing RAG matching and explicitly instructing the model to treat context as truth mitigated this issue.
3. **Session State Rerendering**: In Streamlit, button presses cause page reloads. We managed feedback key generation using unique index strings to prevent state loss during evaluations.

---

## 8. Reflection Answers (Task 9)

### 1. What are the main components of your deployed LLM system?
- **Streamlit Frontend**: Chat interface and status dashboard.
- **FastAPI Backend**: Handles API routing, RAG context retrieval, logging, and error handling.
- **Local RAG Store**: Standard JSON storage (`faq_data.json`) containing official university policies.
- **Ollama LLM Server**: Hosts and runs the local `llama3.2:1b` model.
- **Audit Logs**: File-based logging of student requests, model outputs, and feedback ratings.

### 2. Why is FastAPI useful in this pipeline?
FastAPI is highly asynchronous, supports fast serialization/deserialization via Pydantic, automatically generates OpenAPI docs (`/docs`), and can handle parallel queries efficiently. It separates the presentation layer (frontend) from model query logic and business rules.

### 3. What role does your chosen LLM model play?
The `llama3.2:1b` model synthesizes the raw retrieved context into natural, polite, and human-like answers. It handles grammatical variations, translates the official FAQ rules into conversational language, and answers follow-up general inquiries.

### 4. What role does the frontend play?
The Streamlit frontend provides a user-friendly conversational interface. It abstracts away backend API requests, handles UI states (loading spinners, offline notices), checks the system health, and lets users submit response ratings.

### 5. What is the difference between running the model locally and using an external API?
- **Local Model**: Zero API costs, complete privacy/data security (questions never leave the host machine), runs entirely offline, but is constrained by local CPU/GPU performance.
- **External API (e.g. Gemini, OpenAI)**: Superior general reasoning, no local hardware setup needed, but introduces recurring subscription/token costs, latency dependencies, and potential privacy risks for sensitive data.

### 6. What security risks may exist if this system is deployed in an organisation?
- **Prompt Injection**: Students attempting to override system prompts to change grades or exam schedules.
- **Data Privacy**: If logging contains sensitive student registration details, ID numbers, or emails.
- **Denial of Service (DoS)**: High-frequency queries causing CPU/GPU exhaustion on the self-hosted server.

### 7. What improvements would be needed before deploying this system in production?
- **Vector Embeddings Database**: Transition from simple keyword-based matching to a Vector Database (e.g., ChromaDB, pgvector) with semantic embeddings (e.g., HuggingFace embeddings) for superior retrieval.
- **Authentication & Authorization**: Simple API keys, OAuth2, or integration with the university's Single Sign-On (SSO).
- **Containerization**: Deploying backend, database, and model via Docker and Kubernetes for automated scaling.

### 8. How would you monitor the system in real-world use?
- Monitor request latency and generation time.
- Track error rates (5xx statuses) and connection errors to Ollama.
- Analyze feedback logs (`feedback.json`) to track user ratings (percentage of "Poor" ratings) to catch poor retrieval results.
- Hardware telemetry: GPU VRAM utilization, CPU load, and RAM usage.

### 9. How would you protect sensitive student information?
- Anonymize or redact personal details (ID cards, phone numbers) before logging or sending them to the LLM.
- Encrypt data at rest (database, logs) and transit (TLS/HTTPS for API endpoints).
- Clear session histories upon logout or timeout.

### 10. What challenges did you face during implementation?
Managing python dependencies across environments, integrating simple keyword retrieval without heavy ML libraries, and coordinating Streamlit states when rating messages were major challenges. These were solved by structured formatting, utilizing Pydantic settings, and logging exceptions cleanly.

---

## 9. Conclusion
This implementation demonstrates that self-hosted Small Language Models (SLMs) like `llama3.2:1b` coupled with lightweight RAG pipelines can effectively solve specific enterprise requirements (like university student support) with zero external API dependencies, complete privacy, and rapid local responses.

---

## 10. Appendix: Running instructions
### 1. Requirements Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Backend
```bash
uvicorn backend.main:app --port 8000 --reload
```

### 3. Run Frontend
```bash
streamlit run frontend/app.py
```
