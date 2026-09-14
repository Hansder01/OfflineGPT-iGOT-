import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import DocumentModel
from backend.rag_engine import index_document_content
from backend.utils import extract_text_from_file

# Server-Side Verified Educational Curriculum Modules
EDUCATIONAL_CURRICULUM = [
    {
        "filename": "EDU_01_Solar_System_and_Astronomy.txt",
        "title": "Solar System and Astronomy for Kids",
        "content": "The Solar System consists of the Sun and eight planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Earth is the third planet from the Sun and the only planet known to support life. The Moon is Earth's natural satellite. Light from the Sun takes approximately 8 minutes to reach Earth."
    },
    {
        "filename": "EDU_02_Mathematics_and_Geometry.txt",
        "title": "Fundamental Mathematics and Geometry Principles",
        "content": "Mathematics is the science of numbers, shapes, and patterns. Geometry studies the properties of shapes such as triangles, circles, squares, and cubes. The area of a rectangle is calculated as length times width. The perimeter is the total distance around the outside of a shape."
    },
    {
        "filename": "EDU_03_World_Geography_and_Continents.txt",
        "title": "World Geography, Oceans, and Continents",
        "content": "Earth has seven continents: Asia, Africa, North America, South America, Antarctica, Europe, and Australia. Asia is the largest continent by both land area and population. The planet has five major oceans: Pacific, Atlantic, Indian, Southern, and Arctic Oceans."
    },
    {
        "filename": "EDU_04_World_History_Milestones.txt",
        "title": "Milestones of Ancient Civilizations and World History",
        "content": "Ancient Egypt developed along the Nile River and built magnificent pyramids. The Indus Valley Civilization established planned cities with advanced drainage systems. Ancient Greece introduced democratic governance, philosophy, and the Olympic Games."
    },
    {
        "filename": "EDU_05_Computer_Coding_for_Beginners.txt",
        "title": "Computer Programming Concepts for Young Learners",
        "content": "Programming is writing instructions for computers using code. Key programming concepts include variables, loops, conditional statements, and functions. Python is an easy-to-learn programming language used by scientists, educators, and software engineers worldwide."
    },
    {
        "filename": "EDU_06_Physics_Forces_and_Energy.txt",
        "title": "Introduction to Physics, Motion, and Energy",
        "content": "Physics is the branch of science concerned with nature and properties of matter and energy. Energy exists in kinetic, potential, thermal, electrical, and chemical forms. Newton's laws of motion describe how objects move and interact under gravitational forces."
    },
    {
        "filename": "EDU_07_Biology_Plants_and_Ecosystems.txt",
        "title": "Plant Life, Photosynthesis, and Natural Ecosystems",
        "content": "Plants produce food through photosynthesis, converting sunlight, water, and carbon dioxide into oxygen and glucose. Ecosystems are communities of living organisms interacting with their physical environment. Biodiversity ensures healthy ecosystems."
    },
    {
        "filename": "EDU_08_Environmental_Science_and_Earth.txt",
        "title": "Environmental Protection, Recycling, and Climate Science",
        "content": "Environmental science studies interactions between human systems and the natural world. Recycling paper, plastic, and metals conserves natural resources and reduces landfill waste. Renewable energy sources include solar power, wind energy, and hydroelectricity."
    },
    {
        "filename": "EDU_09_Literature_Reading_and_Poetry.txt",
        "title": "Reading Comprehension, Grammar, and Creative Writing",
        "content": "Reading expands vocabulary, comprehension, and imagination. Grammar rules govern sentence structure, punctuation, and parts of speech (nouns, verbs, adjectives, adverbs). Creative writing allows students to craft stories, poems, and essays."
    },
    {
        "filename": "EDU_10_Digital_Safety_and_Ethics_for_Kids.txt",
        "title": "Digital Safety, Online Ethics, and Privacy Protection",
        "content": "Digital safety involves protecting personal information online. Students should never share passwords, home addresses, or private details with strangers on the internet. Cyberbullying prevention and respectful communication build positive online learning communities."
    }
]

def load_server_educational_kb(db: Session) -> int:
    """
    Generates and indexes server-verified educational files into educational_kb/
    """
    settings.EDUCATIONAL_KB_DIR.mkdir(parents=True, exist_ok=True)
    indexed_count = 0
    
    for item in EDUCATIONAL_CURRICULUM:
        fname = item["filename"]
        file_path = settings.EDUCATIONAL_KB_DIR / fname
        
        # Write text content if file doesn't exist on server
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"=== {item['title']} ===\n\n{item['content']}\n")
                
        # Check if indexed in DB
        existing = db.query(DocumentModel).filter(DocumentModel.filename == fname).first()
        if existing:
            continue
            
        file_size = file_path.stat().st_size
        extracted_text = extract_text_from_file(file_path, ".txt")
        
        doc_model = DocumentModel(
            filename=fname,
            original_filename=fname,
            file_type=".txt",
            file_size=file_size,
            user_id=None # Server-side document
        )
        db.add(doc_model)
        db.commit()
        db.refresh(doc_model)
        
        index_document_content(db, doc_model, extracted_text)
        indexed_count += 1
        
    return indexed_count
