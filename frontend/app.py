import streamlit as st
import requests
import json
import os
import datetime

# Page Configuration
st.set_page_config(
    page_title="University Student Support Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Endpoint Configuration
BACKEND_URL = os.getenv("API_BACKEND_URL", "http://localhost:8000")
FEEDBACK_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "logs", "feedback.json")

# Ensure directory for feedback exists
os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

# Custom Premium Styling
st.markdown("""
<style>
    /* Styling elements for a premium modern look */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .status-card {
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    
    .status-badge {
        font-size: 0.9rem;
        font-weight: 600;
        padding: 0.3rem 0.6rem;
        border-radius: 20px;
        display: inline-block;
    }
    
    .status-online {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    .status-degraded {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.3);
    }
    
    .status-offline {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .rag-tag {
        font-size: 0.8rem;
        background: linear-gradient(90deg, rgba(168, 85, 247, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%);
        color: #c084fc;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        border: 1px solid rgba(168, 85, 247, 0.4);
        display: inline-block;
        margin-top: 0.5rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to save feedback
def save_feedback(question, answer, rating):
    feedback_data = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    feedback_data = json.loads(content)
        except Exception:
            feedback_data = []
            
    feedback_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
        "rating": rating
    }
    feedback_data.append(feedback_entry)
    
    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(feedback_data, f, indent=2)
        st.toast(f"Thank you for rating this response as **{rating}**!", icon="💾")
    except Exception as e:
        st.error(f"Failed to save feedback: {str(e)}")

# Initialize Session State for Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fetch Backend Health
backend_status = "offline"
health_info = {}
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=3.0)
    if response.status_code == 200:
        health_info = response.json()
        if health_info.get("status") == "healthy":
            backend_status = "online"
        else:
            backend_status = "degraded"
except Exception:
    backend_status = "offline"

# SIDEBAR
with st.sidebar:
    st.image("https://img.icons8.com/nolan/256/university.png", width=100)
    st.markdown("### System Dashboard")
    
    # Connection Health Checks
    if backend_status == "online":
        st.markdown(
            f'<div class="status-card">'
            f'Backend API: <span class="status-badge status-online">Connected</span><br>'
            f'Local LLM: <span class="status-badge status-online">Running</span><br>'
            f'<small style="color:#64748b;">Model: {health_info.get("model_configured")}</small>'
            f'</div>', 
            unsafe_allow_html=True
        )
    elif backend_status == "degraded":
        st.markdown(
            f'<div class="status-card">'
            f'Backend API: <span class="status-badge status-online">Connected</span><br>'
            f'Local LLM: <span class="status-badge status-degraded">Disconnected</span><br>'
            f'<small style="color:#ef4444;">{health_info.get("llm_message", "LLM Down")}</small>'
            f'</div>', 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="status-card">'
            f'Backend API: <span class="status-badge status-offline">Offline</span><br>'
            f'Local LLM: <span class="status-badge status-offline">Unknown</span><br>'
            f'<small style="color:#ef4444;">Is FastAPI backend running on port 8000?</small>'
            f'</div>', 
            unsafe_allow_html=True
        )

    # General FAQ Guide / Features
    st.markdown("### Supported Queries")
    st.markdown(
        "- 📝 **Course Registration** (deadlines, portals)\n"
        "- 📝 **Examination Rules** (grading, medical issues)\n"
        "- 📚 **Library Services** (borrowing, overdue fines)\n"
        "- 💻 **ICT Support** (campus Wi-Fi, password reset)\n"
        "- 🏠 **Hostel Application** (allocation, fees)\n"
        "- 💰 **Fee Payment** (installments, exam cards)\n"
        "- 📅 **Academic Calendar** (semester dates, breaks)\n"
        "- ⚖️ **Student Conduct** (dress codes, student IDs)"
    )

    st.markdown("---")
    st.markdown("### System Info")
    st.info("Uses a local Small Language Model (SLM) integrated with a Retrieval-Augmented Generation (RAG) database.")

# MAIN INTERFACE
st.markdown('<h1 class="main-title">UniSupport AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Instant university assistance powered by self-hosted LLM & FAQ RAG</p>', unsafe_allow_html=True)

# Connection Warning Overlay
if backend_status == "offline":
    st.error("🔴 **Cannot establish connection to the backend API.** Please start the FastAPI backend server (`uvicorn backend.main:app --reload`) to enable chat.")
elif backend_status == "degraded":
    st.warning("⚠️ **LLM Model Offline.** The FastAPI server is running, but it cannot connect to the local Ollama LLM engine. Please ensure Ollama is running and has the model pulled.")

# Display Chat History
for index, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Additional metadata badges
        if msg["role"] == "assistant":
            if msg.get("rag_used"):
                st.markdown(f'<span class="rag-tag">✓ RAG Augmented ({msg.get("category")})</span>', unsafe_allow_html=True)
            
            # Rating feedback widget (Only if not already rated)
            feedback_key = f"rating_{index}"
            if feedback_key not in st.session_state:
                cols = st.columns([1, 1, 1, 15])
                with cols[0]:
                    if st.button("👍 Good", key=f"good_{index}"):
                        st.session_state[feedback_key] = "Good"
                        save_feedback(msg["question"], msg["content"], "Good")
                        st.rerun()
                with cols[1]:
                    if st.button("😐 Avg", key=f"avg_{index}"):
                        st.session_state[feedback_key] = "Average"
                        save_feedback(msg["question"], msg["content"], "Average")
                        st.rerun()
                with cols[2]:
                    if st.button("👎 Poor", key=f"poor_{index}"):
                        st.session_state[feedback_key] = "Poor"
                        save_feedback(msg["question"], msg["content"], "Poor")
                        st.rerun()
            else:
                st.caption(f"Rated: **{st.session_state[feedback_key]}**")

# Student Query Input
if prompt := st.chat_input("Ask a question about courses, exams, library, hostels, fees..."):
    # Render user query in chat
    with st.chat_message("user"):
        st.write(prompt)
    
    # Store query in session history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare response holder
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # If backend is offline, don't attempt API call
        if backend_status == "offline":
            error_response = "Backend is currently offline. Please ensure the backend is started before typing."
            response_placeholder.error(error_response)
            st.session_state.messages.append({"role": "assistant", "content": error_response, "question": prompt, "rag_used": False, "category": "Error"})
        else:
            with st.spinner("Analyzing rules & generating response..."):
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/ask",
                        json={"question": prompt},
                        timeout=35.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        ans = data["answer"]
                        rag_used = data["rag_used"]
                        category = data["category"]
                        
                        # Render answer
                        response_placeholder.write(ans)
                        if rag_used:
                            st.markdown(f'<span class="rag-tag">✓ RAG Augmented ({category})</span>', unsafe_allow_html=True)
                        
                        # Store in history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": ans,
                            "question": prompt,
                            "rag_used": rag_used,
                            "category": category
                        })
                        
                        # Force refresh to render feedback buttons correctly
                        st.rerun()
                    else:
                        error_detail = res.json().get("detail", "Unknown server error.")
                        response_placeholder.error(f"Error ({res.status_code}): {error_detail}")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Backend Error: {error_detail}",
                            "question": prompt,
                            "rag_used": False,
                            "category": "Error"
                        })
                except requests.exceptions.Timeout:
                    timeout_error = "The request to the server timed out. The local LLM is taking too long to generate a response."
                    response_placeholder.error(timeout_error)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": timeout_error,
                        "question": prompt,
                        "rag_used": False,
                        "category": "Error"
                    })
                except Exception as e:
                    connection_error = f"Failed to communicate with backend: {str(e)}"
                    response_placeholder.error(connection_error)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": connection_error,
                        "question": prompt,
                        "rag_used": False,
                        "category": "Error"
                    })
