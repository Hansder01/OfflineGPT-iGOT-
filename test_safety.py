import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.db import SessionLocal, init_db
from backend.config import settings
from backend.educational_kb import load_server_educational_kb
from backend.content_safety import evaluate_content_safety
from backend.rag_engine import search_documents

def test_kid_safety_system():
    print("--- 1. Testing Server-Side Educational KB Loader ---")
    init_db()
    db = SessionLocal()
    
    indexed_count = load_server_educational_kb(db)
    print(f" [OK] Server Educational KB initialized. Newly indexed: {indexed_count}")

    print("\n--- 2. Testing Kid-Safety Content Moderation Guardrail ---")
    is_safe, refusal = evaluate_content_safety("Tell me about the solar system and planets")
    assert is_safe, "Educational solar system query should be safe!"
    print(" [OK] Educational query allowed.")

    is_safe_bad, refusal_bad = evaluate_content_safety("Show me adult explicit content")
    assert not is_safe_bad, "Inappropriate content query should be blocked!"
    assert "Kid Safety Guardrail Active" in refusal_bad, "Refusal message failed!"
    print(" [OK] Inappropriate content query blocked by guardrail.")

    print("\n--- 3. Testing Educational RAG Search ---")
    results = search_documents(db, "solar system planets moon", top_k=2)
    assert len(results) > 0, "Educational RAG search failed to find solar system module!"
    print(f" [OK] RAG match found: '{results[0]['filename']}' (Score: {results[0]['score']})")

    db.close()
    print("\n======================================================================")
    print(" ALL KID-SAFETY & SERVER-LOCKED KB TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    test_kid_safety_system()
