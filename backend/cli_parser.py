import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.rate_limiter import get_rate_limit_info
from backend.rag_engine import search_documents
from backend.agentic_llm import execute_agent_tool, generate_agent_response
from backend.utils import get_system_telemetry

def parse_and_execute_cli(cmd_text: str, db: Session, user_id: Optional[int] = None, identifier: str = "default") -> Dict[str, Any]:
    """
    Parses custom CLI command prompt inputs starting with '/' or plain prompt.
    Returns structured output object for terminal UI rendering.
    """
    cmd = cmd_text.strip()
    
    if not cmd:
        return {"type": "info", "output": ""}
        
    # Command: /help
    if cmd.lower() in ["/help", "/?", "help"]:
        help_text = """
🖥️  OFFLINE GPT CLI TERMINAL COMMANDS:
----------------------------------------------------------------------
  /help                           Display this help menu
  /rag search <query>             Search indexed document knowledge base
  /agent math <expression>        Execute safe mathematical evaluation
  /sysinfo                        Display system telemetry & CPU/RAM status
  /limit                          Show rate limiting status & cooldown timer
  /config get                     View active LLM mode & API key status
  /config set mode <mode>         Set LLM mode (auto | offline | gemini | groq)
  /clear                          Clear terminal screen output
  
  [Any text without '/']          Send normal agentic AI prompt
----------------------------------------------------------------------
"""
        return {"type": "cli_output", "command": cmd, "output": help_text}

    # Command: /clear
    if cmd.lower() in ["/clear", "clear"]:
        return {"type": "clear", "command": cmd, "output": "Terminal screen cleared."}

    # Command: /sysinfo
    if cmd.lower() in ["/sysinfo", "/status", "sysinfo", "status"]:
        telemetry = get_system_telemetry()
        output = f"""
💻 SYSTEM TELEMETRY & HEALTH REPORT:
----------------------------------------------------------------------
  Platform OS       : {telemetry.get('os')}
  Architecture      : {telemetry.get('architecture', 'N/A')}
  Python Version    : {telemetry.get('python_version')}
  CPU Usage         : {telemetry.get('cpu_usage_percent')}%
  RAM Usage         : {telemetry.get('memory_used_gb')} GB / {telemetry.get('memory_total_gb')} GB ({telemetry.get('memory_percent')}%)
  Disk Usage        : {telemetry.get('disk_used_gb')} GB / {telemetry.get('disk_total_gb')} GB
  Engine Mode       : {settings.LLM_MODE.upper()}
  System Status     : {telemetry.get('status')}
----------------------------------------------------------------------
"""
        return {"type": "cli_output", "command": cmd, "output": output}

    # Command: /limit
    if cmd.lower() in ["/limit", "/quota"]:
        rate_info = get_rate_limit_info(db, identifier)
        output = f"""
🛡️ SECURITY & RATE LIMIT STATUS:
----------------------------------------------------------------------
  Identifier        : {identifier}
  Prompts Used      : {rate_info['current_count']} / {rate_info['max_prompts']}
  Remaining Quota   : {rate_info['remaining']} prompts
  Window Duration   : {rate_info['window_seconds']} seconds ({rate_info['window_seconds']//60} mins)
  Reset Countdown   : {rate_info['reset_in_seconds']} seconds
  Cooldown Active   : {"YES 🔴 (Locked until timer resets)" if rate_info['cooldown_active'] else "NO 🟢 (Operational)"}
----------------------------------------------------------------------
"""
        return {"type": "cli_output", "command": cmd, "output": output}

    # Command: /config get
    if cmd.lower() == "/config get":
        output = f"""
⚙️ CURRENT ENVIRONMENT CONFIGURATION:
----------------------------------------------------------------------
  LLM Mode          : {settings.LLM_MODE}
  Gemini API Key    : {"Configured ✅" if settings.GEMINI_API_KEY else "Not set ❌ (Free key at aistudio.google.com)"}
  Groq API Key      : {"Configured ✅" if settings.GROQ_API_KEY else "Not set ❌ (Free key at console.groq.com)"}
  HuggingFace Key   : {"Configured ✅" if settings.HF_API_KEY else "Not set ❌"}
  Ollama Base URL   : {settings.OLLAMA_BASE_URL} ({settings.OLLAMA_MODEL})
  Rate Limit        : {settings.RATE_LIMIT_PROMPTS} prompts / {settings.RATE_LIMIT_WINDOW_SECONDS}s
----------------------------------------------------------------------
"""
        return {"type": "cli_output", "command": cmd, "output": output}

    # Command: /config set mode <mode>
    if cmd.lower().startswith("/config set mode"):
        parts = cmd.split()
        if len(parts) >= 4:
            new_mode = parts[3].lower()
            if new_mode in ["auto", "offline", "gemini", "groq"]:
                settings.LLM_MODE = new_mode
                return {"type": "cli_output", "command": cmd, "output": f"✅ LLM Mode successfully updated to: '{new_mode}'."}
        return {"type": "cli_output", "command": cmd, "output": "❌ Usage: /config set mode <auto|offline|gemini|groq>"}

    # Command: /rag search <query>
    if cmd.lower().startswith("/rag search"):
        query = cmd[11:].strip()
        if not query:
            return {"type": "cli_output", "command": cmd, "output": "❌ Usage: /rag search <your search query>"}
        
        results = search_documents(db, query, top_k=settings.MAX_SEARCH_RESULTS, user_id=user_id)
        if not results:
            output = f"🔍 RAG Search query: '{query}'\nNo matching documents found in Knowledge Base."
        else:
            output = f"🔍 RAG KNOWLEDGE BASE SEARCH RESULTS FOR: '{query}'\n"
            output += "======================================================================\n"
            for i, r in enumerate(results, 1):
                output += f"[{i}] File: {r['filename']} | Score: {r['score']} | Chunk: #{r['chunk_index']}\n"
                output += f"    Content: {r['content'][:250]}...\n\n"
        return {"type": "cli_output", "command": cmd, "output": output}

    # Command: /agent math <expr>
    if cmd.lower().startswith("/agent math") or cmd.lower().startswith("/calc"):
        expr = cmd.replace("/agent math", "").replace("/calc", "").strip()
        if not expr:
            return {"type": "cli_output", "command": cmd, "output": "❌ Usage: /agent math <expression>"}
        
        tool_res = execute_agent_tool("math_calculator", {"expression": expr})
        if "error" in tool_res:
            output = f"❌ Math Error: {tool_res['error']}"
        else:
            output = f"🧮 Math Evaluation:\n  Input  : {expr}\n  Result : {tool_res['result']}"
        return {"type": "cli_output", "command": cmd, "output": output}

    # Unknown slash command
    if cmd.startswith("/"):
        return {"type": "cli_output", "command": cmd, "output": f"❌ Unknown command: '{cmd}'. Type '/help' for available CLI commands."}

    # Default: Execute as regular Agentic Prompt through CLI
    result = generate_agent_response(cmd, db, user_id=user_id, mode=settings.LLM_MODE)
    output = f"🤖 [{result['provider_used']}]\n{result['response']}"
    return {"type": "cli_output", "command": cmd, "output": output}
