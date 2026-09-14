import json
import math
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import DocumentModel, DocumentChunk

# Common English Stopwords to prevent spurious RAG keyword matching
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "can", "cannot", "could", "did", "do", "does", "doing", "down", "during", "each", 
    "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", 
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", 
    "let", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", 
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", 
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", 
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", 
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", 
    "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves", "make", "step", 
    "process", "tell", "explain", "give", "show"
}

# Try importing sentence_transformers, with fallback to TF-IDF cosine similarity
SENTENCE_TRANSFORMER_AVAILABLE = False
embed_model = None

try:
    from sentence_transformers import SentenceTransformer
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    SENTENCE_TRANSFORMER_AVAILABLE = True
except Exception:
    pass

def get_embedding(text: str) -> List[float]:
    """Generates vector embedding for input text."""
    if SENTENCE_TRANSFORMER_AVAILABLE and embed_model is not None:
        try:
            return embed_model.encode(text).tolist()
        except Exception:
            pass
    
    # Filter stopwords for TF-IDF style term frequency vector fallback
    raw_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in raw_words if w not in STOPWORDS]
    freqs: Dict[str, float] = {}
    for w in words:
        freqs[w] = freqs.get(w, 0.0) + 1.0
    
    norm = math.sqrt(sum(v*v for v in freqs.values())) or 1.0
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
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = (overlap_text + "\n\n" + p) if overlap_text else p
            
    if current_chunk:
        chunks.append(current_chunk)
        
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
    """
    Performs semantic vector search across indexed document chunks.
    Uses meaningful content words (stopwords removed) and enforces strict relevance threshold.
    """
    # Extract substantive query keywords (ignore common filler words)
    raw_query_words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
    substantive_query_words = set(w for w in raw_query_words if w not in STOPWORDS)
    
    # If query has no substantive keywords, do not match random documents
    if not substantive_query_words:
        return []
        
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
    
    for chunk, doc in results_raw:
        score = 0.0
        if chunk.vector_data:
            try:
                c_vec = json.loads(chunk.vector_data)
                score = cosine_similarity_vectors(query_vec, c_vec)
            except Exception:
                score = 0.0
                
        # Keyword matching bonus based ONLY on substantive words
        chunk_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', chunk.content.lower()))
        common_words = substantive_query_words.intersection(chunk_words)
        
        # Only reward if actual substantive query words appear in chunk!
        if common_words:
            keyword_ratio = len(common_words) / len(substantive_query_words)
            score += keyword_ratio * 0.6
        else:
            # If NONE of the substantive query keywords exist in the chunk, penalize score
            score *= 0.1
            
        # Strict relevance threshold: ignore unrelated chunks
        if score >= 0.35:
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
