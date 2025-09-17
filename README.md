# LexiLens AI

Production-Grade Legal Document Intelligence Platform

## Overview

LexiLens AI is a sophisticated SaaS platform that leverages state-of-the-art AI to deconstruct, analyze, and simplify complex legal documents. It empowers professionals to make informed decisions with confidence, speed, and unparalleled clarity.

## Tech Stack

- **Frontend:** Streamlit (Python)
- **Backend:** FastAPI (Python)
- **AI:** Google Gemini API with LangChain
- **Database:** Supabase PostgreSQL (with SQLite fallback)
- **PDF Processing:** PyMuPDF & pdfplumber
- **Authentication:** JWT tokens
- **Deployment:** Ready for Docker deployment

## Features

- 🔍 **Intelligent Document Analysis** - AI-powered legal document deconstruction
- ⚠️ **Advanced Risk Classification** - Automated identification of high-risk clauses
- 📝 **Context-Aware Simplification** - Plain English summaries of complex legal text
- 🔎 **Semantic Search** - AI-powered document search and retrieval
- 🎯 **What-If Scenario Analysis** - Test legal scenarios against your documents
- 🔐 **Secure User Authentication** - JWT-based authentication system
- 📊 **Beautiful UI** - Professional dark theme with responsive design
- 🚀 **Developer-First API** - Comprehensive REST API with automatic documentation

## Project Structure

```
lexilens-ai/
├── app.py                 # Main Streamlit application
├── backend/               # FastAPI backend
│   ├── main.py           # Main API application
│   ├── models.py         # SQLAlchemy database models
│   ├── auth.py           # Authentication utilities
│   ├── __init__.py       # Package initialization
│   └── .env              # Environment variables
├── frontend/             # Additional frontend components
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Python 3.10+
- Supabase account (for database) or SQLite (fallback)
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Krish-Garg01/lexilens-ai.git
   cd lexilens-ai
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create `.env` file in the `backend/` directory:
   ```bash
   cd backend
   ```

   Create or edit `.env`:
   ```properties
   # Google Gemini API Key (required)
   GEMINI_API_KEY=your_gemini_api_key_here

   # Supabase Database URL (optional - falls back to SQLite)
   SUPABASE_DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```

4. **Run the application**

   **Option A: Run both frontend and backend**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python main.py

   # Terminal 2 - Frontend
   streamlit run ../app.py
   ```

   **Option B: Run individual services**
   ```bash
   # Backend only
   cd backend
   python main.py

   # Frontend only
   streamlit run app.py
   ```

### API Keys Setup

1. **Google Gemini API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Add it to `backend/.env` as `GEMINI_API_KEY`

2. **Supabase Database (Optional):**
   - Create account at [Supabase](https://supabase.com)
   - Create a new project
   - Go to Settings → Database → Connection string
   - Copy the URI and add to `backend/.env` as `SUPABASE_DATABASE_URL`

## Usage

### Web Interface
- **Frontend:** Visit `http://localhost:8501`
- **Features:**
  - User registration and login
  - Document upload and analysis
  - Search through documents
  - Scenario analysis
  - View analysis history

### API Usage
- **Backend API:** Visit `http://localhost:8000/docs` for interactive API documentation
- **Health Check:** `GET /health`
- **Authentication:** `POST /token`
- **Document Analysis:** `POST /analyze`
- **Search:** `POST /search`
- **Scenarios:** `POST /scenario`

### Example API Usage

```python
import requests

# Login
response = requests.post("http://localhost:8000/token",
    data={"username": "test@example.com", "password": "test123"})
token = response.json()["access_token"]

# Upload and analyze document
headers = {"Authorization": f"Bearer {token}"}
with open("legal_document.pdf", "rb") as f:
    response = requests.post("http://localhost:8000/analyze",
        files={"file": f}, headers=headers)

print(response.json())
```

## Development

### Database Setup
The application automatically creates database tables on startup. If using Supabase, ensure your connection string is correct. If not, it falls back to SQLite.

### Testing
```bash
# Run backend tests
cd backend
python -m pytest

# Test API endpoints
python test_api_key.py
python test_db.py
python test_health.py
```

### Environment Variables
- `GEMINI_API_KEY`: Required for AI functionality
- `SUPABASE_DATABASE_URL`: Optional, enables cloud database

## Deployment

### Docker (Future)
```bash
# Build and run with Docker
docker build -t lexilens-ai .
docker run -p 8000:8000 -p 8501:8501 lexilens-ai
```

### Production Deployment
1. Set up production Supabase database
2. Configure environment variables
3. Use a production WSGI server (gunicorn)
4. Set up reverse proxy (nginx)
5. Enable HTTPS

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use type hints for function parameters and return values
- Write comprehensive docstrings
- Add tests for new features

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not configured"**
   - Ensure your API key is set in `backend/.env`
   - Verify the key starts with "AIza"

2. **Database connection errors**
   - Check your Supabase URL if using Supabase
   - Ensure database credentials are correct
   - Falls back to SQLite if Supabase fails

3. **PDF processing errors**
   - Ensure PDF files are not corrupted
   - Check file permissions
   - Try different PDF formats

4. **Authentication issues**
   - Default test user: `test@example.com` / `test123`
   - Register new users via the API or frontend

### Logs
Check the console output for detailed error messages and debugging information.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for legal professionals worldwide**
