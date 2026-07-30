import os
import sys
from pathlib import Path
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.config import settings
from backend.db import SessionLocal, init_db
from backend.models import DocumentModel
from backend.rag_engine import index_document_content, search_documents
from backend.utils import extract_text_from_file

# List of 20 Source PDF Titles & Contents
PDF_SOURCES = [
    {
        "filename": "01_AI_and_Agentic_Systems.pdf",
        "title": "Agentic AI Architecture and Autonomous Decision Systems",
        "content": "Agentic AI refers to artificial intelligence systems capable of autonomous decision making, tool execution, and multi-step reasoning. Unlike simple passive chat models, agentic systems maintain dynamic state, interact with external environments, run command lines, and query vector databases via Retrieval-Augmented Generation (RAG). Autonomous agents utilize specialized tools like file search, math calculators, and API interfaces."
    },
    {
        "filename": "02_Quantum_Computing_Overview.pdf",
        "title": "Quantum Mechanics & Superconducting Qubit Architectures",
        "content": "Quantum computing uses quantum bits (qubits) capable of superposition and entanglement. Superconducting qubits operate at cryogenic temperatures near absolute zero. Shor's algorithm provides exponential speedup for integer factorization, while Grover's algorithm accelerates unstructured database searches."
    },
    {
        "filename": "03_Cybersecurity_Best_Practices.pdf",
        "title": "Zero Trust Network Architecture & Rate Limiting Controls",
        "content": "Zero Trust Security operates under the principle of never trust, always verify. Security rate limiting controls protect API endpoints against denial-of-service (DoS) attacks and brute force token guessing. Sliding window rate limiters enforce quota caps and cooldown reset windows."
    },
    {
        "filename": "04_Data_Science_and_Analytics.pdf",
        "title": "Exploratory Data Analysis and Feature Engineering Pipelines",
        "content": "Data science encompasses data ingestion, cleaning, transformation, and statistical modeling. Feature engineering creates domain-specific input features for machine learning algorithms. Cross-validation prevents overfitting and measures model generalization performance."
    },
    {
        "filename": "05_Cloud_Architecture_Guide.pdf",
        "title": "Multi-Cloud Infrastructure and Microservices Orchestration",
        "content": "Cloud architecture organizes computing resources into scalable infrastructure-as-a-service (IaaS), platform-as-a-service (PaaS), and serverless architectures. Microservices decouple applications into containerized services managed by Kubernetes."
    },
    {
        "filename": "06_Blockchain_and_Smart_Contracts.pdf",
        "title": "Decentralized Ledger Technology and Cryptographic Hashing",
        "content": "Blockchain is an immutable, distributed ledger secured by cryptographic hash functions like SHA-256. Consensus algorithms such as Proof of Work (PoW) and Proof of Stake (PoS) ensure agreement among decentralized network nodes."
    },
    {
        "filename": "07_Machine_Learning_Pipelines.pdf",
        "title": "Supervised Learning, Model Deployment, and MLOps",
        "content": "Machine learning pipelines automate training, evaluation, model registration, and deployment. Supervised learning models include linear regression, decision trees, random forests, and gradient boosted trees."
    },
    {
        "filename": "08_DevOps_and_CI_CD_Automation.pdf",
        "title": "Continuous Integration, Continuous Deployment, and Monitoring",
        "content": "DevOps integrates software development and IT operations. CI/CD pipelines automate testing, code linting, building container images, and deploying updates to production with zero downtime."
    },
    {
        "filename": "09_Database_Management_Systems.pdf",
        "title": "Relational Databases, ACID Transactions, and Vector Search",
        "content": "Relational database management systems (RDBMS) adhere to ACID principles: Atomicity, Consistency, Isolation, and Durability. Modern databases also support vector search extensions for storing high-dimensional embeddings."
    },
    {
        "filename": "10_Full_Stack_Web_Development.pdf",
        "title": "FastAPI, Modern Javascript UI, and Glassmorphism CSS",
        "content": "Full stack web development combines backend REST/GraphQL APIs with interactive user interfaces. Glassmorphism CSS design uses backdrop filters, vibrant purple gradients, and dark mode obsidian themes."
    },
    {
        "filename": "11_Robotics_and_Automation.pdf",
        "title": "Robot Operating System (ROS) and Kinematic Path Planning",
        "content": "Robotics combines mechanical engineering, electronics, and autonomous control software. Robot Operating System (ROS) enables node-based publish-subscribe message passing."
    },
    {
        "filename": "12_Natural_Language_Processing.pdf",
        "title": "Transformer Architectures, Attention Mechanisms, and RAG",
        "content": "Natural Language Processing (NLP) uses deep learning models to understand human text. Self-attention mechanisms enable transformers like BERT and GPT to process contextual relationships."
    },
    {
        "filename": "13_Computer_Vision_Fundamentals.pdf",
        "title": "Convolutional Neural Networks and Object Detection",
        "content": "Computer Vision extracts insight from digital images and video streams. Convolutional Neural Networks (CNNs) extract spatial features using convolution kernels, pooling layers, and classification heads."
    },
    {
        "filename": "14_IoT_and_Embedded_Systems.pdf",
        "title": "Internet of Things Protocols and Edge Computing",
        "content": "Internet of Things (IoT) connects physical sensors and microcontrollers to local networks and cloud platforms. Protocols like MQTT and CoAP transmit lightweight telemetry payloads."
    },
    {
        "filename": "15_Software_Engineering_Principles.pdf",
        "title": "SOLID Design Principles and Clean Architecture",
        "content": "Software engineering enforces design principles for maintainability: Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion (SOLID)."
    },
    {
        "filename": "16_Network_Security_Protocols.pdf",
        "title": "TLS Encryption, PKI, and Firewall Infrastructure",
        "content": "Network security protects data transmission using Transport Layer Security (TLS), Public Key Infrastructure (PKI), and cryptographic key exchange algorithms like RSA and Diffie-Hellman."
    },
    {
        "filename": "17_Big_Data_Processing_Frameworks.pdf",
        "title": "Distributed Computing with Apache Spark and Hadoop",
        "content": "Big Data frameworks process large-scale structured and unstructured datasets across compute clusters. Apache Spark uses Resilient Distributed Datasets (RDDs) and in-memory execution."
    },
    {
        "filename": "18_Microservices_Architecture.pdf",
        "title": "API Gateways, Event-Driven Services, and Message Queues",
        "content": "Microservices break monolithic applications into autonomous services communicating over HTTP/gRPC APIs or event buses like Apache Kafka and RabbitMQ."
    },
    {
        "filename": "19_AI_Ethics_and_Governance.pdf",
        "title": "Responsible AI, Bias Mitigation, and Regulatory Compliance",
        "content": "AI ethics addresses algorithmic fairness, transparency, data privacy, and explainability. Responsible AI frameworks establish guardrails against bias and unauthorized data usage."
    },
    {
        "filename": "20_Operating_System_Design.pdf",
        "title": "Kernel Memory Management, Virtualization, and Scheduling",
        "content": "Operating systems manage hardware resources, process scheduling, memory allocation, and virtual file systems. Preemptive scheduling ensures fair CPU time slice allocation."
    }
]

def generate_pdf_files():
    init_db()
    db = SessionLocal()
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#8b5cf6'),
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10
    )

    print("======================================================================")
    print(" GENERATING & INDEXING 20 SOURCE PDF DOCUMENTS INTO KNOWLEDGE BASE")
    print("======================================================================")

    created_count = 0
    for item in PDF_SOURCES:
        pdf_filename = item["filename"]
        pdf_path = settings.UPLOADS_DIR / pdf_filename
        
        # Build PDF using ReportLab
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        story = [
            Paragraph(item["title"], title_style),
            Spacer(1, 10),
            Paragraph(item["content"], body_style),
            Spacer(1, 15),
            Paragraph(f"Document Source ID: {pdf_filename} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style)
        ]
        doc.build(story)

        # Check if already in DB
        existing = db.query(DocumentModel).filter(DocumentModel.filename == pdf_filename).first()
        if existing:
            db.delete(existing)
            db.commit()

        file_size = pdf_path.stat().st_size
        extracted_text = extract_text_from_file(pdf_path, ".pdf")
        
        doc_model = DocumentModel(
            filename=pdf_filename,
            original_filename=pdf_filename,
            file_type=".pdf",
            file_size=file_size,
            user_id=None # Public document
        )
        db.add(doc_model)
        db.commit()
        db.refresh(doc_model)
        
        chunks = index_document_content(db, doc_model, extracted_text)
        created_count += 1
        print(f" [OK] Generated & Indexed: '{pdf_filename}' ({chunks} chunks, {file_size} bytes)")

    db.close()
    print("======================================================================")
    print(f" SUCCESSFULLY CREATED & INDEXED ALL {created_count} PDF DOCUMENTS!")
    print("======================================================================")

if __name__ == "__main__":
    generate_pdf_files()
