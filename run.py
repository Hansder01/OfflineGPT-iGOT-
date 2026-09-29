import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_app():
    print("======================================================================")
    print(" STARTING OFFLINE GPT - AGENTIC RAG & CUSTOM COMMAND PROMPT PLATFORM")
    print("======================================================================")
    
    # Ensure database directory exists
    db_dir = BASE_DIR / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize DB
    from backend.db import init_db
    init_db()
    print(" [OK] SQLite Database Initialized.")
    
    import uvicorn
    import atexit
    
    print(" [INIT] Starting Ollama server...")
    try:
        ollama_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(" [OK] Ollama server started in background.")
        
        def kill_ollama():
            print("\n [SHUTDOWN] Stopping Ollama server...")
            ollama_process.terminate()
            try:
                ollama_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                ollama_process.kill()
            print(" [OK] Ollama server stopped.")
            
        atexit.register(kill_ollama)
    except FileNotFoundError:
        print(" [WARN] 'ollama' command not found. Ensure Ollama is installed and in PATH.")
    except Exception as e:
        print(f" [WARN] Failed to start Ollama: {e}")

    print(" [OK] Launching Web UI & FastAPI Server on http://127.0.0.1:8000")
    print("======================================================================")
    
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    run_app()
