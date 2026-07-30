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

# Tool Definitions for Agentic AI
TOOLS = [
    {
        "name": "rag_search",
        "description": "Searches stored offline documents for information.",
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
            # Safe math evaluation using math module namespace
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
    
    full_text = f"{system_context}\n\nUser Question:\n{prompt}" if system_context else prompt
    payload = {
        "contents": [
            {
                "parts": [{"text": full_text}]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"[Gemini API Error] {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[Gemini Exception] {e}")
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
    
    messages = []
    if system_context:
        messages.append({"role": "system", "content": system_context})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"[Groq API Error] {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[Groq Exception] {e}")
        return None

def call_ollama_local(prompt: str, system_context: str = "") -> Optional[str]:
    """Calls local Ollama instance."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": f"{system_context}\n\n{prompt}" if system_context else prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=8)
        if response.status_code == 200:
            return response.json().get("response", "")
    except Exception:
        pass
    return None

def local_smart_fallback_agent(prompt: str, tool_outputs: List[Dict[str, Any]], rag_sources: List[Dict[str, Any]]) -> str:
    """Intelligent offline fallback engine when no cloud API keys are set."""
    p_lower = prompt.lower()
    
    # 1. RAG Context response
    if rag_sources and any(s["score"] > 0.1 for s in rag_sources):
        response = "🤖 **[Offline RAG Engine Response]**\n\n"
        response += "Based on your indexed documents, here is what I found:\n\n"
        for i, s in enumerate(rag_sources, 1):
            if s["score"] > 0.1:
                response += f"**Source {i}: `{s['filename']}` (Match Score: {int(s['score']*100)}%)**\n"
                response += f"> \"{s['content'][:300]}...\"\n\n"
        response += "*Note: You can add your free Gemini or Groq API key in `.env` to enable cloud neural synthesis on top of these RAG search results!*"
        return response
        
    # 2. Tool output response
    if tool_outputs:
        response = "🛠️ **[Agentic Tool Output]**\n\n"
        for output in tool_outputs:
            t = output.get("tool")
            if t == "math_calculator":
                response += f"**Math Calculation Result:**\n`{output.get('expression')}` = **{output.get('result')}**\n"
            elif t == "system_diagnostics":
                tele = output.get("telemetry", {})
                response += f"**System Health Metrics:**\n"
                response += f"- OS: `{tele.get('os')}`\n"
                response += f"- CPU Usage: `{tele.get('cpu_usage_percent')}%`\n"
                response += f"- RAM Usage: `{tele.get('memory_used_gb')} GB / {tele.get('memory_total_gb')} GB ({tele.get('memory_percent')}%)`\n"
                response += f"- Disk Usage: `{tele.get('disk_used_gb')} GB / {tele.get('disk_total_gb')} GB`\n"
            elif t == "datetime_lookup":
                response += f"**System Date & Time:**\nDate: `{output.get('date')}` | Time: `{output.get('time')}`\n"
        return response

    # 3. Conversational Fallbacks
    if "hello" in p_lower or "hi" in p_lower or "hey" in p_lower:
        return "👋 **Hello! Welcome to Offline GPT & Agentic RAG Platform.**\n\nI am your intelligent assistant. You can:\n1. 📄 Upload documents to search & query them in RAG mode.\n2. 💻 Use the interactive **Command Prompt CLI** (`/help`, `/sysinfo`, `/rag search`).\n3. ⚡ Configure free API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) in `.env` for deep AI generation."
    elif "who are you" in p_lower or "about" in p_lower or "what can you do" in p_lower:
        return "🧠 **Offline GPT Agentic Platform v1.0**\n\nI am a privacy-first AI agent platform that runs locally offline and supports retrieval-augmented generation (RAG), tool execution, rate limiting, and terminal command integration."
    else:
        return f"💡 **Offline Agent Note:** I received your prompt: *\"{prompt}\"*.\n\nTo enable full generative LLM responses, please paste your free Gemini API key (`GEMINI_API_KEY`) or Groq API key (`GROQ_API_KEY`) inside the `.env` file.\n\nYou can also upload files in the **Knowledge Base** tab to search your documents offline!"

def generate_agent_response(prompt: str, db: Session, user_id: Optional[int] = None, mode: str = "auto") -> Dict[str, Any]:
    """
    Main Agentic Orchestrator:
    1. Analyzes prompt & selects tools (RAG, Math, System Telemetry)
    2. Executes tools & gathers context
    3. Dispatches to selected AI provider (Gemini -> Groq -> Ollama -> Fallback)
    """
    tool_outputs = []
    rag_sources = []
    p_lower = prompt.lower()
    
    # Autonomous Tool Selection Scenarios
    # 1. Math calculation request
    if re.search(r'(\d+[\+\-\*\/\%\^]\d+)|calculate|compute|math', p_lower):
        math_match = re.search(r'([0-9\.\s\+\-\*\/\%\^\(\)]+)', prompt)
        if math_match and len(math_match.group(1).strip()) > 2:
            out = execute_agent_tool("math_calculator", {"expression": math_match.group(1).strip()})
            tool_outputs.append(out)
            
    # 2. System info request
    if "system" in p_lower or "cpu" in p_lower or "ram" in p_lower or "memory" in p_lower or "status" in p_lower or "telemetry" in p_lower:
        out = execute_agent_tool("system_diagnostics", {})
        tool_outputs.append(out)
        
    # 3. Date / Time request
    if "time" in p_lower or "date" in p_lower or "today" in p_lower or "clock" in p_lower:
        out = execute_agent_tool("datetime_lookup", {})
        tool_outputs.append(out)
        
    # 4. RAG Document Search (Default if documents exist or query looks like a question/search)
    rag_search_out = execute_agent_tool("rag_search", {"query": prompt}, db=db, user_id=user_id)
    if rag_search_out.get("results"):
        rag_sources = rag_search_out["results"]
        tool_outputs.append(rag_search_out)

    # Build System Context for LLM Synthesis
    system_context = "You are Offline GPT, an intelligent agentic AI platform.\n"
    if rag_sources:
        system_context += "\nRelevant Document Context:\n"
        for i, s in enumerate(rag_sources, 1):
            system_context += f"[Document {i}: {s['filename']}]\n{s['content']}\n\n"
    if tool_outputs:
        system_context += f"\nAgent Tool Execution Results:\n{json.dumps(tool_outputs, indent=2)}\n"

    answer = None
    provider_used = "Fallback Engine"

    # Try Provider Cascade based on settings / mode
    if mode == "gemini" or (mode == "auto" and settings.GEMINI_API_KEY):
        answer = call_gemini_api(prompt, system_context)
        if answer:
            provider_used = "Google Gemini (Free Tier)"

    if not answer and (mode == "groq" or (mode == "auto" and settings.GROQ_API_KEY)):
        answer = call_groq_api(prompt, system_context)
        if answer:
            provider_used = "Groq Llama-3.1 (Free Tier)"

    if not answer and (mode == "offline" or mode == "auto"):
        answer = call_ollama_local(prompt, system_context)
        if answer:
            provider_used = f"Local Ollama ({settings.OLLAMA_MODEL})"

    if not answer:
        answer = local_smart_fallback_agent(prompt, tool_outputs, rag_sources)
        provider_used = "Offline Agentic Engine"

    return {
        "prompt": prompt,
        "response": answer,
        "provider_used": provider_used,
        "tools_executed": [t.get("tool") for t in tool_outputs if "tool" in t],
        "rag_sources": rag_sources
    }
