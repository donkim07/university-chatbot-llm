import os
import json
import datetime
import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.llm_client import LLMClient

# Ensure logs directory exists
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

# Central Logging Configuration
logger = logging.getLogger("backend_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Add stdout handler for debugging
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

app = FastAPI(
    title="University Student Support Assistant API",
    description="Backend API for retrieving support information augmented with an LLM.",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = LLMClient()

class AskRequest(BaseModel):
    question: str = Field(..., description="The query from the student.")

class AskResponse(BaseModel):
    question: str
    answer: str
    category: str
    rag_used: bool
    timestamp: str

@app.get("/health")
async def health_check():
    """
    Checks the system health status, verifying connection to the local LLM.
    """
    llm_ok, llm_msg = await llm_client.check_ollama_health()
    return {
        "status": "healthy" if llm_ok else "degraded",
        "backend": "online",
        "llm_connected": llm_ok,
        "llm_message": llm_msg,
        "model_configured": settings.llm_model,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Accepts student questions, checks and retrieves FAQ context (RAG),
    asks the local LLM, logs details, and returns responses.
    """
    question = request.question.strip()
    
    # Empty question check
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty. Please enter a valid question."
        )

    logger.info(f"Received Question: '{question}'")

    try:
        # Generate response using LLM & RAG
        result = await llm_client.generate_response(question, use_rag=True)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Log interaction to file
        log_msg = (
            f"Question: '{question}' | "
            f"Answer: '{result['answer']}' | "
            f"Category: {result['category']} | "
            f"RAG: {result['rag_used']} | "
            f"Matched FAQ: {result['matched_faq']}"
        )
        logger.info(f"Successful Interaction: {log_msg}")

        return AskResponse(
            question=question,
            answer=result["answer"],
            category=result["category"],
            rag_used=result["rag_used"],
            timestamp=timestamp
        )

    except ConnectionError as ce:
        error_msg = f"LLM client connection error: {str(ce)}"
        logger.error(f"Error processing question: '{question}' - {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local LLM is not available. Please ensure Ollama is running. Error details: {str(ce)}"
        )

    except TimeoutError as te:
        error_msg = f"LLM generation timed out: {str(te)}"
        logger.error(f"Error processing question: '{question}' - {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The local LLM service took too long to generate a response. Please try again."
        )

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Error processing question: '{question}' - {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating response: {str(e)}"
        )


class FeedbackRequest(BaseModel):
    question: str = Field(..., description="The student's original query.")
    answer: str = Field(..., description="The assistant's generated response.")
    rating: str = Field(..., description="The rating: Good, Average, or Poor.")


@app.post("/feedback")
async def receive_feedback(request: FeedbackRequest):
    feedback_file = os.path.join(os.path.dirname(settings.log_file), "feedback.json")
    feedback_data = []
    
    if os.path.exists(feedback_file):
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    feedback_data = json.loads(content)
        except Exception as e:
            logger.error(f"Error reading feedback file: {str(e)}")
            
    feedback_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": request.question,
        "answer": request.answer,
        "rating": request.rating
    }
    feedback_data.append(feedback_entry)
    
    try:
        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2)
        logger.info(f"Received user feedback: Question: '{request.question[:30]}...' | Rating: {request.rating}")
        return {"status": "success", "message": "Feedback saved successfully."}
    except Exception as e:
        logger.error(f"Failed to save feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)}"
        )
