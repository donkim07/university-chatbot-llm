# Implementation Plan: University Student Support Assistant

This document outlines the step-by-step implementation plan for the **University Student Support Assistant** assignment, including the migration to an **Angular** frontend.

---

## 1. Expected Architecture & Flow

```mermaid
graph TD
    User([Student / User]) <--> Frontend[Angular Frontend: web/ (port 4200)]
    Frontend <--> Backend[FastAPI Backend: backend/ (port 8000)]
    Backend <--> Ollama[Ollama Local Engine]
    Ollama <--> Model[LLM: llama3.2:1b]
    Backend -.-> Logs[(App Log: backend/logs/app.log)]
    Backend -.-> FAQ[(FAQ Knowledge Base: backend/faq_data.json)]
```

---

## 2. Directory Structure

The project has the following layout:

```
support-assistant-llm/
├── backend/
│   ├── main.py            # FastAPI endpoints, logging, and error handling
│   ├── llm_client.py      # Ollama API client & simple RAG logic
│   ├── config.py          # Port config, model configurations, Ollama URL
│   ├── faq_data.json      # FAQ data for the Simple RAG option
│   └── logs/
│       └── app.log        # Interaction log (timestamp, Q&A, errors)
├── web/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.ts     # Angular component (logic and HTTP client)
│   │   │   ├── app.html   # Angular layout (glassmorphism chat view)
│   │   │   └── app.css    # Animations and custom styling
│   │   └── styles.css     # Global styles (Tailwind v4 import)
│   ├── package.json       # Node package descriptors
│   └── pnpm-lock.yaml     # Lockfile for pnpm
├── tests/
│   └── test_api.py        # Automated backend API testing script
├── docs/
│   ├── screenshots/       # Evidence screenshots for submission
│   └── report.md          # Technical report draft and answers to reflection questions
├── requirements.txt       # Dependencies list (FastAPI, requests, etc.)
├── PLAN.md                # Project execution plan (This file)
└── README.md              # Project instructions and usage guide
```

---

## 3. Step-by-Step Execution Plan

### Phase 1: Environment & Tooling Setup
1. **Virtual Environment**: Create and activate a Python virtual environment (`.venv`).
2. **Dependencies**: Create a `requirements.txt` with:
   - `fastapi`, `uvicorn` (Backend API)
   - `requests` (API requests & testing)
   - `pydantic`, `pydantic-settings` (Config validation)
   - `httpx` (Asynchronous HTTP requests)
3. **Local LLM**:
   - Pull `llama3.2:1b` using Ollama (`ollama pull llama3.2:1b`).
   - Validate model responsiveness locally.

### Phase 2: Configuration & Backend Development
1. **Config**: Write `backend/config.py` to load environment variables/settings (e.g. host, port, Ollama base URL, model name).
2. **LLM Client**: Write `backend/llm_client.py` using `httpx` to send chat requests to the Ollama endpoint.
3. **FastAPI App (`backend/main.py`)**:
   - Centralized logging to `backend/logs/app.log`.
   - Setup CORS middleware to allow communication from the Angular frontend.
   - Implement the `/health` endpoint (checks backend readiness and Ollama engine connection).
   - Implement the `/ask` endpoint (receives student questions, retrieves FAQ RAG context, queries Ollama, and logs the interaction).
   - Implement the `/feedback` endpoint (receives ratings Good/Average/Poor from the browser client and records it in `backend/logs/feedback.json`).

### Phase 3: Frontend Development (`web/src/app`)
1. **Bootstrap Config (`app.config.ts`)**: Add `provideHttpClient()` to enable API connection.
2. **Component Logic (`app.ts`)**:
   - Define type declarations and model interfaces.
   - Use Angular Signals to track reactive state (`messages`, `userQuery`, `isLoading`, `systemStatus`).
   - Implement backend checks for health and `/ask` queries.
   - Coordinate feedback rating event handlers.
3. **Responsive Template (`app.html`)**:
   - Use Tailwind CSS and glassmorphic panels for a modern chat layout.
   - Render real-time status metrics (API online, LLM online).
   - Inject input validation and pulsing bounces for thinking stages.
4. **Custom Styling (`app.css`)**: Implement slide-in message entries and responsive custom scrollbars.

### Phase 4: Simple RAG Integration (Option B Extension)
1. **Knowledge Base**: Store common university questions and answers (e.g. course registration schedules, hostel deadlines, exam codes) inside `backend/faq_data.json`.
2. **Retriever**: Implement Jaccard similarity word-overlap retriever in `backend/llm_client.py`.
3. **Augmentation**: Retrieve relevant FAQ QA context and prefix it as truth context inside the chat request.

### Phase 5: Automated Testing (`tests/test_api.py`)
1. Create a script to run automated tests.
2. Test both positive test cases (successful `/health` check and a sample `/ask` request) and negative cases (e.g. sending empty questions, testing behavior when Ollama is stopped).

### Phase 6: Report and Screenshot Evidence
1. Write a markdown draft (`docs/report.md`) detailing the implementation steps and reflection answers.
2. Provide guide on capturing screenshots.
