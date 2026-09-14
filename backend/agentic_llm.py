import requests
import json
import re
import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.rag_engine import search_documents
from backend.utils import get_system_telemetry
from backend.content_safety import evaluate_content_safety, sanitize_output

# Tool Definitions for Agentic AI
TOOLS = [
    {
        "name": "rag_search",
        "description": "Searches stored offline educational documents for information.",
        "parameters": ["query"]
    },
    {
        "name": "math_calculator",
        "description": "Evaluates safe math expressions.",
        "parameters": ["expression"]
    },
    {
        "name": "system_diagnostics",
        "description": "Retrieves hardware and backend platform metrics.",
        "parameters": []
    },
    {
        "name": "datetime_lookup",
        "description": "Gets current date and local system time.",
        "parameters": []
    }
]

# Strict Non-Negotiable Educational Guardrail Prompt for Llama 3.2 & Cloud LLMs
LOCKED_EDUCATIONAL_SYSTEM_PROMPT = """
You are Offline GPT, an educational AI tutor designed strictly for children and students.
NON-NEGOTIABLE SAFETY CONSTRAINTS:
1. You must ONLY answer educational, academic, scientific, mathematical, historical, geographical, coding, and school-related questions.
2. You must NEVER generate or explain content related to:
   - Adult, erotic, or sexual topics
   - Weapons, firearms, explosives, bomb-making, or hazardous chemicals/poisons
   - Drugs, narcotics, or illegal substances
   - Violence, physical self-harm, or suicide
   - Hacking, cyberattacks, password cracking, or malicious software
3. If any user asks about inappropriate, violent, or hazardous content, you MUST refuse and state:
   "I cannot answer that. I am an educational tutor here to help you learn school subjects like Science, Math, History, Astronomy, and Coding. What educational topic can we explore today?"
4. Keep all responses encouraging, accurate, easy to understand, and age-appropriate.
"""

def execute_agent_tool(tool_name: str, args: Dict[str, Any], db: Optional[Session] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Executes agentic tool call."""
    if tool_name == "rag_search":
        query = args.get("query", "")
        if not db:
            return {"error": "Database session unavailable for RAG search."}
        results = search_documents(db, query, top_k=settings.MAX_SEARCH_RESULTS, user_id=user_id)
        return {
            "tool": "rag_search",
            "query": query,
            "match_count": len(results),
            "results": results
        }
    elif tool_name == "math_calculator":
        expr = args.get("expression", "")
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            allowed_names.update({"abs": abs, "round": round, "pow": pow})
            clean_expr = re.sub(r'[^0-9\+\-\*\/\%\(\)\.\,\s\^]', '', expr).replace('^', '**')
            result = eval(clean_expr, {"__builtins__": None}, allowed_names)
            return {
                "tool": "math_calculator",
                "expression": expr,
                "result": result
            }
        except Exception as e:
            return {
                "tool": "math_calculator",
                "expression": expr,
                "error": f"Invalid math expression: {str(e)}"
            }
    elif tool_name == "system_diagnostics":
        return {
            "tool": "system_diagnostics",
            "telemetry": get_system_telemetry()
        }
    elif tool_name == "datetime_lookup":
        now = datetime.now()
        return {
            "tool": "datetime_lookup",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "iso": now.isoformat()
        }
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def call_gemini_api(prompt: str, system_context: str = "") -> Optional[str]:
    """Calls Free Google Gemini REST API."""
    if not settings.GEMINI_API_KEY:
        return None
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    full_text = f"{LOCKED_EDUCATIONAL_SYSTEM_PROMPT}\n\n{system_context}\n\nUser Question:\n{prompt}"
    payload = {
        "contents": [
            {
                "parts": [{"text": full_text}]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return sanitize_output(raw_text)
    except Exception:
        pass
    return None

def call_groq_api(prompt: str, system_context: str = "") -> Optional[str]:
    """Calls Free Groq API (Llama-3.1)."""
    if not settings.GROQ_API_KEY:
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": f"{LOCKED_EDUCATIONAL_SYSTEM_PROMPT}\n{system_context}"},
        {"role": "user", "content": prompt}
    ]
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            return sanitize_output(raw_text)
    except Exception:
        pass
    return None

def call_ollama_local(prompt: str, system_context: str = "") -> Optional[str]:
    """
    Calls local Ollama instance running Llama 3.2 with strict educational safety lock.
    """
    combined_system = f"{LOCKED_EDUCATIONAL_SYSTEM_PROMPT}\n\n{system_context}".strip()
    
    chat_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    chat_payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": combined_system},
            {"role": "user", "content": prompt}
        ],
        "options": {
            "temperature": 0.3,
            "top_p": 0.9
        },
        "stream": False
    }
    
    try:
        response = requests.post(chat_url, json=chat_payload, timeout=8)
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json.get("message", {}).get("content", "")
            if raw_text:
                return sanitize_output(raw_text)
    except Exception:
        pass

    gen_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    gen_payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": f"[SYSTEM: {combined_system}]\n\n[USER: {prompt}]",
        "stream": False
    }
    try:
        response = requests.post(gen_url, json=gen_payload, timeout=8)
        if response.status_code == 200:
            raw_text = response.json().get("response", "")
            if raw_text:
                return sanitize_output(raw_text)
    except Exception:
        pass

    return None

def synthesize_offline_educational_lesson(prompt: str, rag_sources: List[Dict[str, Any]], tool_outputs: List[Dict[str, Any]]) -> str:
    """
    Advanced Local Educational Synthesis Engine:
    Requires strong relevance score (>= 0.35). Never hallucinates unrelated documents.
    """
    p_lower = prompt.lower()
    
    # 1. RAG-Based Educational Synthesis (Requires actual relevant matches)
    valid_sources = [s for s in rag_sources if s.get("score", 0) >= 0.35]
    
    if valid_sources:
        response = f"🎓 **[Educational Knowledge Lesson]**\n\n"
        
        lesson_points = []
        for s in valid_sources:
            clean_content = s["content"].replace('\n', ' ').strip()
            lesson_points.append(clean_content)
            
        full_text = " ".join(lesson_points)
        response += f"{full_text}\n\n"
        
        response += f"### 💡 Key Learning Takeaways:\n"
        sentences = re.split(r'(?<=[.!?]) +', full_text)
        for i, sent in enumerate(sentences[:3], 1):
            if len(sent.strip()) > 10:
                response += f"- **Takeaway {i}:** {sent.strip()}\n"
                
        response += f"\n### 📚 Verified Curriculum Sources:\n"
        for s in valid_sources:
            response += f"- 📄 `{s['filename']}` (Relevance: {int(s['score']*100)}%)\n"
            
        return sanitize_output(response)

    # 2. Tool Output Synthesis
    if tool_outputs:
        response = "🛠️ **[Local Educational Tool Result]**\n\n"
        for output in tool_outputs:
            t = output.get("tool")
            if t == "math_calculator":
                response += f"### 🧮 Mathematical Calculation:\n"
                response += f"- **Expression:** `{output.get('expression')}`\n"
                response += f"- **Result:** **{output.get('result')}**\n"
            elif t == "system_diagnostics":
                tele = output.get("telemetry", {})
                response += f"### 💻 Local Server Telemetry:\n"
                response += f"- **OS:** `{tele.get('os')}`\n"
                response += f"- **CPU Usage:** `{tele.get('cpu_usage_percent')}%`\n"
                response += f"- **RAM:** `{tele.get('memory_used_gb')} GB / {tele.get('memory_total_gb')} GB\n"
            elif t == "datetime_lookup":
                response += f"### 🕒 Date & Time:\n"
                response += f"Date: `{output.get('date')}` | Time: `{output.get('time')}`\n"
        return sanitize_output(response)

    # 3. Conversational Offline Synthesis
    if re.search(r'\b(hello|hi|hey|greetings|morning|afternoon)\b', p_lower):
        return "👋 **Hello Student! Welcome to Offline GPT Educational Edition.**\n\nI am your offline AI learning assistant. Ask me questions about:\n- 🌌 **Solar System & Astronomy**\n- 📐 **Mathematics & Geometry**\n- 🧪 **Physics, Chemistry & Biology**\n- 🌍 **Geography & History**\n- 💻 **Computer Coding in Python**"
    elif re.search(r'\b(who are you|about you|what can you do)\b', p_lower):
        return "🎓 **Offline GPT — Locked Educational AI**\n\nI am a child-safe educational assistant running on your local server. Hazardous and adult content is strictly locked and unaccessible."
    else:
        # Explicit Non-Hallucinating Fallback: No false document matches
        return "📖 **Offline Educational Assistant:**\n\nI could not find information about that in the educational curriculum.\n\nPlease ask a school subject question about:\n- 🌌 **The Solar System & Planets**\n- 📐 **Mathematics & Geometry**\n- 🧪 **Physics, Plants & Ecosystems**\n- 🌍 **World Geography & History**\n- 💻 **Computer Programming Basics**"

def generate_agent_response(prompt: str, db: Session, user_id: Optional[int] = None, mode: str = "auto") -> Dict[str, Any]:
    """
    Main Agentic Orchestrator for Offline & Online Modes with Multi-Layer Safety Guardrails
    """
    # LAYER 1: Immediate Content Safety Evaluation
    is_safe, refusal_msg = evaluate_content_safety(prompt)
    if not is_safe:
        return {
            "prompt": prompt,
            "response": refusal_msg,
            "provider_used": "Kid Safety Guardrail",
            "tools_executed": [],
            "rag_sources": []
        }

    tool_outputs = []
    rag_sources = []
    p_lower = prompt.lower()
    
    # 1. Math calculation request (Strict word boundaries or explicit math operators)
    if re.search(r'\b(calculate|compute|solve math)\b', p_lower) or re.search(r'^\s*[\d\.\(\)]+\s*[\+\-\*\/\^]\s*[\d\.\(\)]+', prompt):
        math_match = re.search(r'([0-9\.\s\+\-\*\/\%\^\(\)]+)', prompt)
        if math_match and len(math_match.group(1).strip()) > 2:
            out = execute_agent_tool("math_calculator", {"expression": math_match.group(1).strip()})
            tool_outputs.append(out)
            
    # 2. System info request (Strict word boundaries - prevents 'tiramisu' matching 'ram'!)
    if re.search(r'\b(system status|telemetry|cpu usage|hardware info|ram usage|memory status)\b', p_lower):
        out = execute_agent_tool("system_diagnostics", {})
        tool_outputs.append(out)
        
    # 3. Date / Time request (Strict word boundaries)
    if re.search(r'\b(current time|what time is it|today\'s date|what date is it|what is the time)\b', p_lower):
        out = execute_agent_tool("datetime_lookup", {})
        tool_outputs.append(out)
        
    # 4. RAG Document Search
    rag_search_out = execute_agent_tool("rag_search", {"query": prompt}, db=db, user_id=user_id)
    if rag_search_out.get("results"):
        rag_sources = rag_search_out["results"]
        tool_outputs.append(rag_search_out)

    # Build System Context for LLM Synthesis
    system_context = ""
    valid_rag_chunks = [s for s in rag_sources if s.get("score", 0) >= 0.35]
    if valid_rag_chunks:
        system_context += "Relevant Educational Curriculum Context:\n"
        for i, s in enumerate(valid_rag_chunks, 1):
            system_context += f"[Document {i}: {s['filename']}]\n{s['content']}\n\n"

    answer = None
    provider_used = "Offline Educational Engine"

    # 1. Try Cloud APIs if configured and connected
    if mode == "gemini" or (mode == "auto" and settings.GEMINI_API_KEY):
        answer = call_gemini_api(prompt, system_context)
        if answer:
            provider_used = "Google Gemini (Free Tier)"

    if not answer and (mode == "groq" or (mode == "auto" and settings.GROQ_API_KEY)):
        answer = call_groq_api(prompt, system_context)
        if answer:
            provider_used = "Groq Llama-3.1 (Free Tier)"

    # 2. Try Local Ollama (Llama 3.2 100% offline neural LLM)
    if not answer and (mode == "offline" or mode == "auto"):
        answer = call_ollama_local(prompt, system_context)
        if answer:
            provider_used = f"Local Llama 3.2 (Offline Safe LLM)"

    # 3. Enhanced Offline Synthesis Engine
    if not answer:
        answer = synthesize_offline_educational_lesson(prompt, valid_rag_chunks, tool_outputs)
        provider_used = "Local Educational Synthesizer"

    # LAYER 3: Guaranteed post-generation safety screening
    safe_answer = sanitize_output(answer)

    return {
        "prompt": prompt,
        "response": safe_answer,
        "provider_used": provider_used,
        "tools_executed": [t.get("tool") for t in tool_outputs if "tool" in t],
        "rag_sources": valid_rag_chunks
    }
