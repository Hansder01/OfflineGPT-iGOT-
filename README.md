# Offline GPT: Skill Intelligence & Capacity Building Platform

An AI-enabled, entirely **offline** learning platform built to strengthen capacity building in India's Official Statistical System. The platform identifies competency gaps, recommends personalized training through an iGOT Karmayogi mock integration, and generates dynamic Quizzes and Multiple Choice Questions (MCQs) directly from uploaded learning materials.

## 🚀 Key Features

1. **Agentic RAG & Secure AI Chat**
   - Upload official PDF documents, guidelines, and manuals into a local vector database.
   - Ask questions and receive context-aware answers powered by a strictly local, server-locked AI (Llama 3.2 via Ollama) to ensure 100% data privacy for sensitive government data.

2. **Automated MCQ & Quiz Generation**
   - Click a single button to instruct the local LLM to automatically read an uploaded document and generate a structured 10-question multiple-choice quiz.
   - Test your knowledge on specific policy documents instantly.

3. **Competency Mapping & User Profiles**
   - A dedicated "Skill Profile" dashboard for officials to log their current roles, educational background, and existing skill sets.
   
4. **Analytics & Engagement Dashboard**
   - Interactive charts (powered by Chart.js) visualizing your Platform Engagement (Prompts, Documents) and Skill Competency Map.
   
5. **iGOT Karmayogi Ecosystem Integration**
   - Automatically cross-references your recorded competency gaps with the official iGOT Karmayogi Course Catalog.
   - Pushes tailored recommendations (e.g., "Advanced R Programming", "Data Visualization") directly to your dashboard.

## 🛠️ Technology Stack
* **Frontend**: HTML5, Vanilla CSS (Glassmorphism UI), Vanilla JavaScript, Chart.js
* **Backend**: Python 3.11, FastAPI, SQLAlchemy (SQLite), Uvicorn
* **AI & LLM**: Ollama (Running `llama3.2` locally), LangChain, HuggingFace Embeddings (all-MiniLM-L6-v2), ChromaDB

## 📦 How to Run (Local Deployment)

This application is designed to run locally without internet access (after initial setup) to comply with strict government data privacy laws.

1. **Activate Virtual Environment**:
   ```bash
   .\venv\Scripts\activate
   ```

2. **Start the Application**:
   Simply run the orchestrator script. This will automatically boot up the local Ollama AI server, initialize the SQLite database, and launch the FastAPI backend!
   ```bash
   python run.py
   ```

3. **Access the Portal**:
   Open your browser and navigate to: `http://127.0.0.1:8000`