# LexiLens AI

Production-Grade Legal Document Intelligence Platform

## Overview

LexiLens AI is a sophisticated SaaS platform that leverages state-of-the-art AI to deconstruct, analyze, and simplify complex legal documents. It empowers professionals to make informed decisions with confidence, speed, and unparalleled clarity.

## Tech Stack

- **Frontend:** Streamlit (Python)
- **Backend:** FastAPI (Python)
- **AI:** Gemini API / OpenAI API with LangChain
- **Database:** PostgreSQL
- **Async Tasks:** Celery & Redis
- **Payments:** Stripe
- **PDF Processing:** PyMuPDF & pdfplumber
- **Vector DB:** ChromaDB / Weaviate
- **Deployment:** Docker & Docker Compose

## Features

- Intelligent document deconstruction
- Advanced risk classification
- Context-aware simplification
- Semantic search engine
- What-If scenario analysis
- Developer-first API

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js (if needed for any JS parts, but currently Python-only)

### Installation

1. Clone the repository
2. Set up frontend:
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Set up backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

### Usage

- Frontend: Visit http://localhost:8501
- Backend API: Visit http://localhost:8000/docs

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
