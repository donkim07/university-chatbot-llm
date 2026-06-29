import json
import logging
import os
import re
import string
import httpx
from typing import Dict, Any, Optional, Tuple, List
from backend.config import settings
from backend.prompts import (
    IMPROVED_SYSTEM_PROMPT,
    RAG_BLEND_SYSTEM_PROMPT,
    GREETING_PATTERNS,
    OFF_TOPIC_KEYWORDS,
)

logger = logging.getLogger("backend_logger")

# Minimum score + confidence required to attach FAQ context to the LLM
RAG_BLEND_THRESHOLD = 0.38
# Only skip the LLM when Ollama is down and we have a solid FAQ match
RAG_FALLBACK_THRESHOLD = 0.45

# Single-word overlaps on these are not enough to trigger RAG
AMBIGUOUS_TOKENS = {
    "security", "help", "support", "student", "university", "udsm", "campus",
    "know", "anything", "about", "tell", "information", "question", "service",
    "office", "rule", "rules", "policy", "policies",
}

SYNONYM_GROUPS = [
    {"register", "registration", "enroll", "enrollment", "signup", "sign"},
    {"exam", "examination", "exams", "test", "tests"},
    {"hostel", "dorm", "dormitory", "accommodation", "room", "hall"},
    {"fee", "fees", "tuition", "payment", "pay"},
    {"library", "books", "borrow", "borrowing", "loan", "lending"},
    {"wifi", "wi-fi", "internet", "network"},
    {"password", "login", "portal", "account", "aris"},
    {"grade", "grading", "gpa", "marks"},
    {"calendar", "semester", "dates", "schedule", "almanac"},
]


class LLMClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model
        self.faq_data: list = []
        self._faq_mtime: float = 0.0
        self.reload_faq_data()

    def reload_faq_data(self) -> int:
        path = settings.faq_data_path
        try:
            mtime = os.path.getmtime(path)
            if mtime == self._faq_mtime and self.faq_data:
                return len(self.faq_data)
            with open(path, "r", encoding="utf-8") as f:
                self.faq_data = json.load(f)
            self._faq_mtime = mtime
            logger.info(f"Loaded {len(self.faq_data)} FAQ entries from {path}")
            return len(self.faq_data)
        except Exception as e:
            logger.error(f"Error loading FAQ from '{path}': {e}")
            self.faq_data = []
            return 0

    def faq_status(self) -> Dict[str, Any]:
        count = self.reload_faq_data()
        path = settings.faq_data_path
        return {
            "faq_entries_loaded": count,
            "faq_data_path": path,
            "faq_file_exists": os.path.isfile(path),
        }

    def _stem(self, word: str) -> str:
        for suffix in ("ing", "tion", "ied", "ies", "ed", "es", "s"):
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                return word[: -len(suffix)]
        return word

    def _clean_and_tokenize(self, text: str) -> set:
        text = text.lower()
        for char in string.punctuation:
            text = text.replace(char, " ")
        words = text.split()

        stopwords = {
            "is", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "do", "does", "how", "what", "where", "when", "why", "my", "your",
            "i", "you", "me", "he", "she", "it", "they", "we", "can", "could", "should",
            "would", "am", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "that", "this", "there", "from", "about", "into", "any", "all", "some",
            "long", "many", "much", "know", "anything", "something", "really", "just",
        }
        raw = {word for word in words if word not in stopwords and len(word) > 1}
        stemmed = {self._stem(w) for w in raw}
        return self._expand_synonyms(raw | stemmed)

    def _expand_synonyms(self, tokens: set) -> set:
        expanded = set(tokens)
        for group in SYNONYM_GROUPS:
            if tokens.intersection(group):
                expanded.update(group)
        return expanded

    def _faq_search_texts(self, faq: Dict[str, Any]) -> List[str]:
        texts = [faq.get("question", "")]
        texts.extend(faq.get("aliases", []))
        return [t for t in texts if t]

    def _faq_keyword_tokens(self, faq: Dict[str, Any]) -> set:
        tokens: set = set()
        for kw in faq.get("keywords", []):
            tokens.update(self._clean_and_tokenize(kw))
        return tokens

    def _is_confident_match(
        self,
        question_tokens: set,
        faq_tokens: set,
        intersection: set,
        score: float,
    ) -> bool:
        if score < RAG_BLEND_THRESHOLD:
            return False

        meaningful = intersection - AMBIGUOUS_TOKENS
        if len(meaningful) >= 2:
            return True
        if len(meaningful) == 1 and score >= 0.55:
            return True
        # High overall score with several overlapping tokens (e.g. near-duplicate question)
        if len(intersection) >= 3 and score >= 0.5:
            return True
        # Only ambiguous overlap (e.g. "security" → dress code FAQ)
        if len(meaningful) == 0:
            return False
        return score >= 0.65

    def retrieve_context(self, question: str) -> Tuple[Optional[Dict[str, Any]], float, bool]:
        """
        Returns (best_faq, score, is_confident).
        """
        self.reload_faq_data()
        if not self.faq_data:
            return None, 0.0, False

        question_tokens = self._clean_and_tokenize(question)
        if not question_tokens:
            return None, 0.0, False

        best_match = None
        best_score = 0.0
        best_confident = False

        for faq in self.faq_data:
            all_faq_tokens: set = set()
            field_scores = []

            for text in self._faq_search_texts(faq):
                faq_tokens = self._clean_and_tokenize(text)
                all_faq_tokens.update(faq_tokens)
                if not faq_tokens:
                    continue
                intersection = question_tokens.intersection(faq_tokens)
                union = question_tokens.union(faq_tokens)
                jaccard = len(intersection) / len(union) if union else 0.0
                recall = len(intersection) / len(question_tokens) if question_tokens else 0.0
                field_scores.append(max(jaccard, recall * 0.9))

            # Keywords contribute but with lower weight — avoids false positives
            kw_tokens = self._faq_keyword_tokens(faq)
            if kw_tokens:
                all_faq_tokens.update(kw_tokens)
                intersection = question_tokens.intersection(kw_tokens)
                if intersection:
                    union = question_tokens.union(kw_tokens)
                    kw_score = len(intersection) / len(union) * 0.75
                    field_scores.append(kw_score)

            if not field_scores:
                continue

            score = max(field_scores)
            intersection = question_tokens.intersection(all_faq_tokens)
            confident = self._is_confident_match(question_tokens, all_faq_tokens, intersection, score)

            if score > best_score:
                best_score = score
                best_match = faq
                best_confident = confident

        if best_match and not best_confident:
            logger.info(
                f"Weak FAQ candidate rejected: '{best_match['question']}' score={best_score:.2f}"
            )
            return None, best_score, False

        return best_match, best_score, best_confident

    def _faq_response(self, faq: Dict[str, Any], score: float, source: str) -> Dict[str, Any]:
        logger.info(f"FAQ {source}: '{faq['question']}' score={score:.2f}")
        return {
            "answer": faq["answer"],
            "category": faq["category"],
            "rag_used": True,
            "matched_faq": faq["question"],
        }

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower().strip())

    def _is_greeting(self, question: str) -> bool:
        q = self._normalize(question)
        if len(q.split()) > 8:
            return False
        return any(
            q == p or q.startswith(p + " ") or q.startswith(p + "!") or q.startswith(p + ",")
            for p in GREETING_PATTERNS
        )

    def _is_off_topic(self, question: str) -> bool:
        q = self._normalize(question)
        return any(kw in q for kw in OFF_TOPIC_KEYWORDS)

    def _greeting_reply(self, question: str) -> str:
        q = self._normalize(question)
        if any(w in q for w in ("thank", "thanks", "bye", "goodbye", "see you")):
            if "bye" in q or "goodbye" in q or "see you" in q:
                return (
                    "Goodbye! Feel free to return anytime you need help with course registration, "
                    "exams, library, ICT, hostels, fees, or other university services."
                )
            return "You're welcome! Let me know if you have any other university-related questions."

        return (
            "Hello! I'm UniSupport AI, your University Student Support Assistant. "
            "I can help with course registration, examinations, the library, ICT support, "
            "hostels, fees, the academic calendar, and student conduct. How can I help you today?"
        )

    def _off_topic_reply(self) -> str:
        return (
            "I'm only able to assist with official university student services such as registration, "
            "examinations, library access, ICT support, hostels, fees, the academic calendar, and "
            "student conduct. I cannot help with hacking, illegal activity, or topics outside this scope. "
            "Please ask a university-related question or contact the Registry for other matters."
        )

    async def check_ollama_health(self) -> Tuple[bool, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags", timeout=3.0)
                if response.status_code != 200:
                    return False, f"Ollama returned status code {response.status_code}"

                models = response.json().get("models", [])
                pulled_models = [m["name"] for m in models]

                found = any(self.model in pm or pm in self.model for pm in pulled_models)
                if not found:
                    return (
                        False,
                        f"Model '{self.model}' is not pulled on local Ollama service. "
                        f"Installed models: {pulled_models}",
                    )

                return True, "Ollama is running and model is available."

            except httpx.ConnectError:
                return False, f"Cannot connect to Ollama at {self.base_url}. Ensure the Ollama service is started."
            except Exception as e:
                return False, f"Ollama connection error: {str(e)}"

    async def _call_llm(
        self,
        question: str,
        system_prompt: str,
        user_content: str,
        history: Optional[list],
        temperature: float = 0.45,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for item in history[-10:]:
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": user_content})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": 320},
                },
                timeout=60.0,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama API returned code {response.status_code}: {response.text}"
                )
            return response.json()["message"]["content"].strip()

    async def generate_response(
        self,
        question: str,
        use_rag: bool = True,
        history: Optional[list] = None,
    ) -> Dict[str, Any]:
        if self._is_greeting(question):
            return {
                "answer": self._greeting_reply(question),
                "category": "Greeting",
                "rag_used": False,
                "matched_faq": None,
            }

        if self._is_off_topic(question):
            return {
                "answer": self._off_topic_reply(),
                "category": "Out of Scope",
                "rag_used": False,
                "matched_faq": None,
            }

        matched_faq = None
        rag_score = 0.0
        rag_confident = False
        if use_rag:
            matched_faq, rag_score, rag_confident = self.retrieve_context(question)

        is_healthy, health_msg = await self.check_ollama_health()
        if not is_healthy:
            if matched_faq and rag_confident and rag_score >= RAG_FALLBACK_THRESHOLD:
                return self._faq_response(matched_faq, rag_score, "fallback")
            raise ConnectionError(health_msg)

        use_rag_context = bool(matched_faq and rag_confident)
        faq_category = matched_faq["category"] if use_rag_context else "General University Support"

        try:
            if use_rag_context:
                logger.info(
                    f"RAG+LLM blend: '{matched_faq['question']}' score={rag_score:.2f}"
                )
                user_content = (
                    f"Official FAQ reference (ground your answer in these facts):\n"
                    f"Topic: {matched_faq['category']}\n"
                    f"Related question: {matched_faq['question']}\n"
                    f"Official answer: {matched_faq['answer']}\n\n"
                    f"Student's question: {question}\n\n"
                    f"Write a helpful, natural reply. Keep all numbers, dates, and fees exact."
                )
                reply = await self._call_llm(
                    question,
                    RAG_BLEND_SYSTEM_PROMPT,
                    user_content,
                    history,
                    temperature=0.4,
                )
            else:
                logger.info(
                    f"LLM-only: '{question}'"
                    + (f" (weak FAQ score {rag_score:.2f})" if rag_score > 0 else "")
                )
                user_content = (
                    f"The student asked a question that did not closely match any official FAQ entry.\n"
                    f"Answer thoughtfully based on general UDSM student services knowledge.\n"
                    f"For ICT, cybersecurity, or portal topics, mention the University Computing Centre (UCC).\n"
                    f"Do not invent specific fees or dates. If unsure, suggest the right office.\n\n"
                    f"Student question: {question}"
                )
                reply = await self._call_llm(
                    question,
                    IMPROVED_SYSTEM_PROMPT,
                    user_content,
                    history,
                    temperature=0.5,
                )

            return {
                "answer": reply,
                "category": faq_category,
                "rag_used": use_rag_context,
                "matched_faq": matched_faq["question"] if use_rag_context else None,
            }

        except httpx.TimeoutException:
            if matched_faq and rag_confident:
                return self._faq_response(matched_faq, rag_score, "timeout-fallback")
            raise TimeoutError("Ollama model took too long to respond.")
        except Exception as e:
            if matched_faq and rag_confident:
                return self._faq_response(matched_faq, rag_score, "error-fallback")
            logger.error(f"Error during Ollama query: {str(e)}")
            raise e
