"""
Simple Ollama integration for AI chat
"""
import requests
from typing import Optional
import os

# Ollama runs on the GPU node (classt21)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://classt21:11434/api/generate")

def query_ollama(prompt: str, model: str = "llama2") -> Optional[str]:
    """
    Query Ollama locally running model
    """
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None


def build_context_prompt(user_question: str, db_context: dict) -> str:
    """
    Build a strict prompt that prevents hallucination
    """
    context_parts = []
    
    # User info
    if db_context.get("user_info"):
        user = db_context["user_info"]
        context_parts.append(f"User Name: {user.get('full_name')}")
        context_parts.append(f"User Role: {user.get('role')}")
        context_parts.append(f"User Email: {user.get('email')}")
    
    # Courses with details
    if db_context.get("courses"):
        context_parts.append("\nEnrolled Courses:")
        for c in db_context["courses"]:
            context_parts.append(f"  - {c['name']} ({c['code']}) - {c.get('members', 'N/A')} members")
    
    # Study sessions
    if db_context.get("study_sessions"):
        context_parts.append(f"\nRecent Study Sessions: {len(db_context['study_sessions'])}")
        for s in db_context["study_sessions"][:3]:  # Only show first 3
            context_parts.append(f"  - {s['title']} ({s['type']})")
    
    # Conversations
    if db_context.get("active_conversations"):
        context_parts.append(f"\nActive Conversations: {db_context['active_conversations']}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are a helpful AI assistant for StudySync, a study collaboration platform.

STRICT RULES:
1. ONLY use information from the context provided below
2. If the answer is not in the context, say "I don't have that information in your current data"
3. Do NOT make up or assume any course details, assignments, deadlines, or other information
4. Do NOT invent features that are not mentioned
5. Be concise and factual

AVAILABLE CONTEXT:
{context}

USER QUESTION: {user_question}

ANSWER (based ONLY on the context above):"""
    
    return prompt
