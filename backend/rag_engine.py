import json
import math
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import DocumentModel, DocumentChunk

# Try importing sentence_transformers, with fallback to TF-IDF cosine similarity
SENTENCE_TRANSFORMER_AVAILABLE = False
embed_model = None

try:
    from sentence_transformers import SentenceTransformer
    # Load lightweight local model
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    SENTENCE_TRANSFORMER_AVAILABLE = True
except Exception as e:
    print(f"[RAG Engine] SentenceTransformers not active, using lightweight internal vector engine: {e}")

def get_embedding(text: str) -> List[float]:
    """Generates vector embedding for input text."""
    if SENTENCE_TRANSFORMER_AVAILABLE and embed_model is not None:
        try:
            return embed_model.encode(text).tolist()
        except Exception:
            pass
    
    # Lightweight TF-IDF style term frequency vector fallback
    words = re.findall(r'\w+', text.lower())
    freqs: Dict[str, float] = {}
    for w in words:
        freqs[w] = freqs.get(w, 0) + 1.0
    
    # Normalize length
    norm = math.sqrt(sum(v*v for v in freqs.values())) or 1.0
    # Store top terms as simple key-val representation
    return [freqs.get(w, 0.0) / norm for w in list(set(words))[:64]]

def cosine_similarity_vectors(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    min_len = min(len(vec1), len(vec2))
    dot = sum(vec1[i] * vec2[i] for i in range(min_len))
    norm1 = math.sqrt(sum(x*x for x in vec1[:min_len]))
    norm2 = math.sqrt(sum(y*y for y in vec2[:min_len]))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Splits raw text into overlapping paragraphs/chunks."""
    if not text:
        return []
    
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Create next chunk with overlap
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = (overlap_text + "\n\n" + p) if overlap_text else p
            
    if current_chunk:
        chunks.append(current_chunk)
        
    # If chunks are still empty or huge, hard split
    if not chunks and text:
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            
    return chunks

def index_document_content(db: Session, doc_model: DocumentModel, text_content: str) -> int:
    """Chunks and indexes document into SQLite vector storage."""
    chunks = chunk_text(text_content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    
    for idx, chunk_str in enumerate(chunks):
        embedding_vector = get_embedding(chunk_str)
        vector_json = json.dumps(embedding_vector)
        
        db_chunk = DocumentChunk(
            document_id=doc_model.id,
            chunk_index=idx,
            content=chunk_str,
            vector_data=vector_json
        )
        db.add(db_chunk)
        
    doc_model.chunk_count = len(chunks)
    db.commit()
    return len(chunks)

def search_documents(db: Session, query: str, top_k: int = 4, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Performs semantic vector search across indexed document chunks."""
    query_vec = get_embedding(query)
    
    query_builder = db.query(DocumentChunk, DocumentModel).join(
        DocumentModel, DocumentChunk.document_id == DocumentModel.id
    )
    
    if user_id is not None:
        query_builder = query_builder.filter(
            (DocumentModel.user_id == user_id) | (DocumentModel.user_id == None)
        )
        
    results_raw = query_builder.all()
    
    scored_chunks = []
    
    # Keyword bonus check
    query_words = set(re.findall(r'\w+', query.lower()))
    
    for chunk, doc in results_raw:
        score = 0.0
        if chunk.vector_data:
            try:
                c_vec = json.loads(chunk.vector_data)
                score = cosine_similarity_vectors(query_vec, c_vec)
            except Exception:
                score = 0.0
                
        # Keyword matching bonus
        chunk_words = set(re.findall(r'\w+', chunk.content.lower()))
        common = query_words.intersection(chunk_words)
        if query_words:
            keyword_bonus = (len(common) / len(query_words)) * 0.4
            score += keyword_bonus
            
        scored_chunks.append({
            "score": round(score, 4),
            "filename": doc.filename,
            "document_id": doc.id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content
        })
        
    # Sort descending by score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]
