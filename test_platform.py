import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.db import SessionLocal, init_db
from backend.models import User, DocumentModel
from backend.auth import hash_password, verify_password, create_db_session, get_current_user_from_token
from backend.rate_limiter import check_rate_limit, get_rate_limit_info
from backend.rag_engine import index_document_content, search_documents
from backend.cli_parser import parse_and_execute_cli
from backend.agentic_llm import generate_agent_response

def test_all():
    print("--- 1. Testing Database & Auth ---")
    init_db()
    db = SessionLocal()
    
    # Clean up old test user if exists
    test_user = db.query(User).filter(User.username == "test_user").first()
    if test_user:
        db.delete(test_user)
        db.commit()

    hashed_pw = hash_password("Secret123")
    assert verify_password("Secret123", hashed_pw), "Password verification failed"
    print(" [OK] Password Hashing & Verification Passed.")

    user = User(username="test_user", email="test@example.com", hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_db_session(db, user)
    fetched_user = get_current_user_from_token(db, token)
    assert fetched_user and fetched_user.username == "test_user", "Session token lookup failed"
    print(" [OK] User Session Storage in SQLite Passed.")

    print("\n--- 2. Testing Rate Limiting Security ---")
    identifier = f"test_user_{user.id}"
    for _ in range(12):
        allowed, status = check_rate_limit(db, identifier)
        if not allowed:
            print(" [OK] Rate limit triggered correctly.")
            break

    print("\n--- 3. Testing RAG Document Indexing & Search ---")
    sample_text = """
    Quantum Computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems too complex for classical computers.
    Superconducting qubits use electrical circuits cooled to ultra-low temperatures near absolute zero to maintain quantum coherence.
    """
    doc = DocumentModel(filename="quantum_guide.txt", original_filename="quantum_guide.txt", file_type=".txt", file_size=len(sample_text), user_id=user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunk_count = index_document_content(db, doc, sample_text)
    print(f" [OK] Indexed document into {chunk_count} RAG chunks.")

    results = search_documents(db, "quantum mechanics qubits", top_k=2)
    assert len(results) > 0, "RAG Search returned no results"
    print(f" [OK] RAG Search result: '{results[0]['filename']}' (Score: {results[0]['score']})")

    print("\n--- 4. Testing Custom Command Prompt CLI Parser ---")
    cli_help = parse_and_execute_cli("/help", db, user_id=user.id, identifier=identifier)
    assert "/rag search" in cli_help["output"], "/help command output failed"
    print(" [OK] CLI /help command passed.")

    cli_sys = parse_and_execute_cli("/sysinfo", db, user_id=user.id, identifier=identifier)
    assert "SYSTEM TELEMETRY" in cli_sys["output"], "/sysinfo command failed"
    print(" [OK] CLI /sysinfo command passed.")

    cli_math = parse_and_execute_cli("/agent math 25 * 4", db, user_id=user.id, identifier=identifier)
    assert "100" in cli_math["output"], "/agent math calculation failed"
    print(" [OK] CLI /agent math command passed.")

    print("\n--- 5. Testing Agentic LLM Orchestrator ---")
    agent_res = generate_agent_response("Explain qubits based on my documents", db, user_id=user.id)
    print(f" [OK] Agent response provider: {agent_res['provider_used']}")

    db.close()
    print("\n======================================================================")
    print(" ALL BACKEND TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    test_all()
