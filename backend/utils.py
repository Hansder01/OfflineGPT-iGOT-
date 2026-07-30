import os
import psutil
import platform
import json
from pathlib import Path
from pypdf import PdfReader
from docx import Document as DocxDocument
import csv

def extract_text_from_file(file_path: Path, file_type: str) -> str:
    """Extracts raw text from PDF, DOCX, TXT, MD, or CSV files."""
    text = ""
    ext = file_type.lower().strip('.')

    try:
        if ext == "pdf":
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif ext in ["docx", "doc"]:
            doc = DocxDocument(str(file_path))
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text += paragraph.text + "\n"
        elif ext == "csv":
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    text += " | ".join(row) + "\n"
        else: # txt, md, json, log, etc.
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        text = f"Error extracting text from {file_path.name}: {str(e)}"

    return text.strip()

def get_system_telemetry() -> dict:
    """Returns hardware and OS system stats for diagnostic view."""
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_usage_percent": cpu_usage,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": disk.percent,
            "status": "Healthy / Operational"
        }
    except Exception:
        return {
            "os": platform.system(),
            "python_version": platform.python_version(),
            "status": "Operational"
        }
