import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import get_db, init_db
from backend.models import User, DocumentModel, DocumentChunk, PromptUsageLog, UserProfile
from backend.auth import (
    hash_password, verify_password, create_access_token,
    create_db_session, get_current_user_from_token, deactivate_session
)
from backend.rate_limiter import check_rate_limit, get_rate_limit_info
from backend.rag_engine import index_document_content, search_documents
from backend.agentic_llm import generate_agent_response, generate_quiz_from_text
from backend.cli_parser import parse_and_execute_cli
from backend.utils import extract_text_from_file, get_system_telemetry
from backend.content_safety import evaluate_content_safety
from backend.educational_kb import load_server_educational_kb

# Initialize DB tables
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Offline GPT — Kid-Safe Educational AI Platform with Server-Locked Knowledge Base"
)

# Load server-side educational KB on startup
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        load_server_educational_kb(db)
    finally:
        db.close()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth helper dependency
def get_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        user = get_current_user_from_token(db, token)
        if user:
            return user
            
    # Fallback: Auto-login for local offline single-user mode
    local_user = db.query(User).filter(User.username == "local_admin").first()
    if not local_user:
        from backend.auth import hash_password
        local_user = User(username="local_admin", email="admin@offline.local", hashed_password=hash_password("admin"))
        db.add(local_user)
        db.commit()
        db.refresh(local_user)
    return local_user

# Rate Limiter dependency helper
def enforce_rate_limit(request: Request, db: Session, user: Optional[User]):
    identifier = f"user_{user.id}" if user else f"ip_{request.client.host}"
    allowed, info = check_rate_limit(db, identifier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=info,
            headers={"Retry-After": str(info.get("reset_in_seconds", 60))}
        )
    return info

# --- AUTH ENDPOINTS ---

@app.post("/api/auth/register")
def register(username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered.")
    
    hashed_pw = hash_password(password)
    user = User(username=username, email=email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_db_session(db, user)
    return {
        "message": "User registered successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email}
    }

@app.post("/api/auth/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    ip_addr = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "")
    token = create_db_session(db, user, ip_address=ip_addr, user_agent=user_agent)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email}
    }

@app.get("/api/auth/me")
def get_current_user_profile(user: Optional[User] = Depends(get_user_optional)):
    if not user:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": {"id": user.id, "username": user.username, "email": user.email, "created_at": user.created_at.isoformat()}
    }

@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        deactivate_session(db, token)
    return {"message": "Logged out successfully"}

@app.get("/api/auth/profile")
def get_user_profile_data(db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        return {}
    import json
    return {
        "designation": profile.designation,
        "department": profile.department,
        "work_experience_years": profile.work_experience_years,
        "educational_qualification": profile.educational_qualification,
        "current_skills": json.loads(profile.current_skills) if profile.current_skills else [],
        "completed_trainings": json.loads(profile.completed_trainings) if profile.completed_trainings else []
    }

@app.post("/api/auth/profile")
def update_user_profile_data(payload: dict, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        
    import json
    if "designation" in payload:
        profile.designation = payload["designation"]
    if "department" in payload:
        profile.department = payload["department"]
    if "work_experience_years" in payload:
        try:
            profile.work_experience_years = float(payload["work_experience_years"])
        except:
            pass
    if "educational_qualification" in payload:
        profile.educational_qualification = payload["educational_qualification"]
    if "current_skills" in payload:
        profile.current_skills = json.dumps(payload["current_skills"])
    if "completed_trainings" in payload:
        profile.completed_trainings = json.dumps(payload["completed_trainings"])
        
    db.commit()
    return {"message": "Profile updated successfully"}

@app.get("/api/analytics/dashboard")
def get_analytics_dashboard(db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    import json
    
    # Get Profile Stats
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    skills_count = 0
    trainings_count = 0
    skills_list = []
    
    if profile:
        skills_list = json.loads(profile.current_skills) if profile.current_skills else []
        skills_count = len(skills_list)
        trainings_list = json.loads(profile.completed_trainings) if profile.completed_trainings else []
        trainings_count = len(trainings_list)
        
    # Get Document Stats
    docs_count = db.query(DocumentModel).count()
    
    # Get Chat/Prompt Stats
    if user.username == "local_admin":
        prompt_count = db.query(PromptUsageLog).count()
    else:
        prompt_count = db.query(PromptUsageLog).filter(PromptUsageLog.user_id == user.id).count()
    
    return {
        "stats": {
            "skills": skills_count,
            "trainings": trainings_count,
            "documents": docs_count,
            "prompts": prompt_count
        },
        "skills_data": skills_list,
        "engagement_data": {
            "labels": ["Prompts Sent", "KB Documents", "Trainings Completed"],
            "data": [prompt_count, docs_count, trainings_count]
        }
    }

# --- iGOT INTEGRATION ENDPOINTS ---
from backend.igot_client import search_igot_courses

@app.post("/api/igot/recommendations")
def get_igot_recommendations(payload: dict, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    skill_gap = payload.get("skill_gap", "")
    if not skill_gap:
        raise HTTPException(status_code=400, detail="skill_gap is required")
        
    courses = search_igot_courses(skill_gap)
    return {"skill_gap": skill_gap, "recommended_courses": courses}

# --- SECURITY & RATE LIMIT ENDPOINTS ---

@app.get("/api/ratelimit/status")
def rate_limit_status(request: Request, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    identifier = f"user_{user.id}" if user else f"ip_{request.client.host}"
    info = get_rate_limit_info(db, identifier)
    return info

@app.get("/api/system/mode")
def system_mode_status():
    return {
        "educational_mode": settings.KIDS_EDUCATIONAL_MODE,
        "server_side_kb_only": settings.SERVER_SIDE_KB_ONLY,
        "profanity_safety_filter": settings.PROFANITY_SAFETY_FILTER,
        "llm_mode": settings.LLM_MODE
    }

# --- CHAT & AGENT ENDPOINTS ---

@app.post("/api/chat")
def chat(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_user_optional)
):
    # Enforce Rate Limiting Security
    rate_info = enforce_rate_limit(request, db, user)
    
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty.")

    # Kid Safety Content Moderation Check
    if settings.PROFANITY_SAFETY_FILTER:
        is_safe, refusal_msg = evaluate_content_safety(prompt)
        if not is_safe:
            return {
                "prompt": prompt,
                "response": refusal_msg,
                "provider_used": "Kid Safety Guardrail",
                "tools_executed": [],
                "rag_sources": [],
                "rate_limit": get_rate_limit_info(db, f"user_{user.id}" if user else f"ip_{request.client.host}")
            }
    
    mode = payload.get("mode", settings.LLM_MODE)
    user_id = user.id if user else None
    
    # Log usage
    log = PromptUsageLog(
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
        prompt_text=prompt,
        is_cli=False
    )
    db.add(log)
    db.commit()
    
    result = generate_agent_response(prompt, db, user_id=user_id, mode=mode)
    result["rate_limit"] = get_rate_limit_info(db, f"user_{user_id}" if user_id else f"ip_{request.client.host}")
    return result

# --- CUSTOM COMMAND PROMPT CLI ENDPOINT ---

@app.post("/api/cli/execute")
def execute_cli(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_user_optional)
):
    cmd_text = payload.get("command", "").strip()
    identifier = f"user_{user.id}" if user else f"ip_{request.client.host}"

    # Kid Safety Content Moderation Check
    if settings.PROFANITY_SAFETY_FILTER and not cmd_text.startswith("/"):
        is_safe, refusal_msg = evaluate_content_safety(cmd_text)
        if not is_safe:
            return {
                "type": "cli_output",
                "command": cmd_text,
                "output": refusal_msg,
                "rate_limit": get_rate_limit_info(db, identifier)
            }
    
    # Check rate limit only if command is an agent prompt
    if not cmd_text.startswith("/") or cmd_text.startswith("/rag"):
        rate_info = enforce_rate_limit(request, db, user)

    # Log usage
    log = PromptUsageLog(
        user_id=user.id if user else None,
        ip_address=request.client.host if request.client else None,
        prompt_text=cmd_text,
        is_cli=True
    )
    db.add(log)
    db.commit()
    
    cli_result = parse_and_execute_cli(cmd_text, db, user_id=user.id if user else None, identifier=identifier)
    cli_result["rate_limit"] = get_rate_limit_info(db, identifier)
    return cli_result

# --- RAG DOCUMENT MANAGEMENT ENDPOINTS ---

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_user_optional)
):
    # Enforce Server-Side KB Lock
    if settings.SERVER_SIDE_KB_ONLY:
        raise HTTPException(
            status_code=403,
            detail="🔒 Knowledge Base is locked in Server-Side Educational Mode. Public file uploads are disabled to protect content safety."
        )

    file_ext = Path(file.filename).suffix.lower()
    allowed_exts = [".pdf", ".txt", ".md", ".docx", ".csv"]
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{file_ext}'. Allowed: {', '.join(allowed_exts)}")

    save_filename = f"{user.id if user else 'public'}_{int(os.times().user)}_{file.filename}"
    save_path = settings.UPLOADS_DIR / save_filename
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    extracted_text = extract_text_from_file(save_path, file_ext)
    file_size = save_path.stat().st_size
    
    doc_model = DocumentModel(
        filename=file.filename,
        original_filename=save_filename,
        file_type=file_ext,
        file_size=file_size,
        user_id=user.id if user else None
    )
    db.add(doc_model)
    db.commit()
    db.refresh(doc_model)
    
    chunk_count = index_document_content(db, doc_model, extracted_text)
    
    return {
        "message": f"File '{file.filename}' uploaded and indexed successfully.",
        "document_id": doc_model.id,
        "filename": doc_model.filename,
        "chunk_count": chunk_count,
        "file_size_bytes": file_size
    }

@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    docs = db.query(DocumentModel).order_by(DocumentModel.upload_date.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "upload_date": d.upload_date.isoformat(),
            "chunk_count": d.chunk_count,
            "is_public": True
        }
        for d in docs
    ]

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    if settings.SERVER_SIDE_KB_ONLY:
        raise HTTPException(
            status_code=403,
            detail="🔒 Knowledge Base is locked in Server-Side Educational Mode. Document deletion is restricted."
        )

    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    db.delete(doc)
    db.commit()
    return {"message": f"Document #{doc_id} deleted successfully."}

@app.post("/api/documents/search")
def search_knowledge_base(payload: dict, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    query = payload.get("query", "").strip()
    if not query:
        return {"results": []}
    results = search_documents(db, query, top_k=settings.MAX_SEARCH_RESULTS, user_id=user.id if user else None)
    return {"query": query, "results": results}

@app.post("/api/documents/{doc_id}/generate_quiz")
def generate_document_quiz(doc_id: int, payload: dict, db: Session = Depends(get_db), user: Optional[User] = Depends(get_user_optional)):
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no text content for quiz generation.")
        
    # Limit to 10 chunks to ensure enough context for 10 questions while balancing CPU usage
    combined_text = "\n\n".join([c.content for c in chunks[:10]])
    
    # Enforce Ollama only for quiz generation
    mode = "offline"
    quiz_data = generate_quiz_from_text(combined_text, mode=mode)
    
    if not quiz_data:
        raise HTTPException(
            status_code=503, 
            detail="AI Quiz Generation failed. Ensure Ollama is running locally."
        )
        
    return {"document_id": doc_id, "filename": doc.filename, "quiz": quiz_data.get("quiz", [])}

# --- SYSTEM TELEMETRY ENDPOINT ---

@app.get("/api/system/info")
def system_info():
    telemetry = get_system_telemetry()
    telemetry["educational_mode"] = settings.KIDS_EDUCATIONAL_MODE
    telemetry["server_side_kb_only"] = settings.SERVER_SIDE_KB_ONLY
    return telemetry

# Mount Frontend Static Directory
app.mount("/css", StaticFiles(directory=settings.FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=settings.FRONTEND_DIR / "js"), name="js")

@app.get("/")
def serve_index():
    return FileResponse(settings.FRONTEND_DIR / "index.html")
