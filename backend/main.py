from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status,Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import shutil
import os
import fitz
import pdfplumber
import json
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


# LangChain Imports (Modernized)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .database import SessionLocal, get_db
from .models import User, Document, Analysis, create_tables
from .auth import authenticate_user, create_access_token, get_current_user, get_password_hash

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# --- Gemini API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")
llm = None  # Initialize llm as None

# Validate API key on startup
if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
    print("❌ ERROR: GEMINI_API_KEY not found or not set in .env file.")
elif not GEMINI_API_KEY.startswith("AIza"):
    print(f"❌ ERROR: GEMINI_API_KEY appears to be invalid (should start with 'AIza'). Current key: {GEMINI_API_KEY[:10]}...")
elif GEMINI_API_KEY != GEMINI_API_KEY.strip():
    print("❌ ERROR: GEMINI_API_KEY contains leading/trailing whitespace.")
else:
    print(f"✅ GEMINI_API_KEY format looks correct: {GEMINI_API_KEY[:10]}...")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
        print("✅ LLM initialized successfully")
    except Exception as e:
        print(f"❌ ERROR initializing LLM: {str(e)}")
        llm = None

# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting LexiLens AI API...")
    if not create_tables():
        print("❌ Failed to create database tables.")
    else:
        print("✅ Database tables ready")

    # Create default test user
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "test@example.com").first():
            hashed_password = get_password_hash("test123")
            test_user = User(email="test@example.com", hashed_password=hashed_password)
            db.add(test_user)
            db.commit()
            print("✅ Default test user created (test@example.com / test123)")
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")
    finally:
        db.close()
    yield
    # Shutdown
    print("👋 Shutting down LexiLens AI API...")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="LexiLens AI API",
    description="Production-Grade Legal Document Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# --- Pydantic Schemas (Response Models) ---
class DocumentOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    class Config: from_attributes = True

class DocumentDetail(DocumentOut):
    content: str
    analysis: Optional[dict] = None

class SearchResult(BaseModel):
    document_id: int
    filename: str
    snippet: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

class ScenarioResponse(BaseModel):
    scenario: str
    analysis: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class AnalysisResponse(BaseModel):
    overall_risk_score: float
    high_risk_clauses: List[dict]
    simplified_summary: str
    processing_time: float
    document_id: int

class RegisterResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str
    message: str
    api_key_status: str
    database: str
    llm_available: bool

class ScenarioRequest(BaseModel):
    scenario_text: str
    
# --- Helper Functions ---
def extract_text_from_pdf(file_path: str) -> str:
    # ... (Your extract_text_from_pdf function remains the same)
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"PyMuPDF failed: {e}, trying pdfplumber...")
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e2:
            print(f"pdfplumber also failed: {e2}")
            raise IOError(f"Could not extract text from PDF: {e} / {e2}")
    if not text.strip():
        raise ValueError("PDF appears to be empty or contains no extractable text")
    return text

def analyze_document_with_ai(text: str) -> dict:
    if llm is None:
        return {
            "overall_risk_score": 0.0,
            "high_risk_clauses": [],
            "simplified_summary": "AI analysis is unavailable due to an API key configuration issue.",
            "processing_time": 0.0,
            "error": "GEMINI_API_KEY not configured properly"
        }
    
    try:
        parser = StrOutputParser()
        # Risk Analysis Chain
        risk_prompt = PromptTemplate.from_template(
            """Analyze the following legal document for risk. Identify clauses related to Termination, Payment terms, Liability, Intellectual property, Confidentiality, and Dispute resolution. For each, provide: 'clause' (quoted text), 'risk' (High, Medium, or Low), 'confidence' (0-1 score), and 'reason'. Also, calculate an 'overall_risk_score' (0-1). Document text: {text}. Output ONLY a valid JSON object with keys: 'overall_risk_score', 'clauses' (a list of dictionaries)."""
        )
        risk_chain = risk_prompt | llm | parser
        risk_result_str = risk_chain.invoke({"text": text})
        
        try:
            risk_result = json.loads(risk_result_str.strip().replace("```json", "").replace("```", ""))
        except json.JSONDecodeError:
            print("⚠️ Warning: Failed to parse JSON from risk analysis. Using fallback.")
            risk_result = {"overall_risk_score": 0.5, "clauses": []}

        # Simplification Chain
        simplify_prompt = PromptTemplate.from_template(
            """Simplify the following legal document into plain English. Focus on key obligations, rights, and risks. Use simple language and explain any legal terms. Document text: {text}. Provide a concise simplified summary."""
        )
        simplify_chain = simplify_prompt | llm | parser
        simplified = simplify_chain.invoke({"text": text})
        
        return {
            "overall_risk_score": risk_result.get("overall_risk_score", 0.5),
            "high_risk_clauses": risk_result.get("clauses", []),
            "simplified_summary": simplified.strip(),
            "processing_time": 5.0  # Placeholder
        }
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        raise e

# --- API Endpoints ---
@app.get("/", tags=["General"])
async def root():
    return {"message": "Welcome to LexiLens AI API"}

@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    return HealthResponse(
        status="healthy" if llm is not None else "degraded",
        message="LexiLens AI API is running",
        api_key_status="configured" if llm is not None else "not_configured",
        database="supabase_connected" if os.getenv("SUPABASE_DATABASE_URL") else "sqlite_fallback",
        llm_available=llm is not None
    )

@app.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    Registers a new user with an email and password.
    """
    # Check if a user with that email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    
    # Create the new user
    hashed_password = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return RegisterResponse(message="User created successfully. Please login.")


@app.post("/token", response_model=TokenResponse, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token, token_type="bearer")

@app.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_document(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        text = extract_text_from_pdf(temp_path)
        
        # Save document to DB
        doc = Document(filename=file.filename, content=text, owner_id=current_user.id)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        analysis_result = analyze_document_with_ai(text)
        
        # Save analysis to DB
        analysis = Analysis(
            document_id=doc.id,
            overall_risk_score=analysis_result["overall_risk_score"],
            high_risk_clauses=json.dumps(analysis_result["high_risk_clauses"]),
            simplified_summary=analysis_result["simplified_summary"],
            processing_time=analysis_result["processing_time"]
        )
        db.add(analysis)
        db.commit()
        
        analysis_result["document_id"] = doc.id
        return analysis_result

    except (IOError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Analysis endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during analysis.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/user/documents", response_model=List[DocumentOut], tags=["Documents"])
async def get_user_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.owner_id == current_user.id).order_by(Document.uploaded_at.desc()).all()

@app.get("/documents/{document_id}", response_model=DocumentDetail, tags=["Documents"])
async def get_document(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    analysis_obj = db.query(Analysis).filter(Analysis.document_id == document_id).order_by(Analysis.created_at.desc()).first()
    
    analysis_data = None
    if analysis_obj:
        analysis_data = {
            "overall_risk_score": analysis_obj.overall_risk_score,
            "high_risk_clauses": json.loads(analysis_obj.high_risk_clauses),
            "simplified_summary": analysis_obj.simplified_summary,
            "processing_time": analysis_obj.processing_time
        }
    
    doc.analysis = analysis_data
    return doc

@app.post("/scenario/{document_id}", response_model=ScenarioResponse, tags=["Analysis"])
async def analyze_scenario_for_document(
    document_id: int,
    request: ScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes a specific what-if scenario based on the content of a single document.
    """
    # Fetch the specific document the user selected
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    scenario_prompt = PromptTemplate.from_template(
        """
        Analyze this legal scenario: "{scenario}"
        
        Based ONLY on the following document content, provide actionable advice and potential risks.
        Refer to specific concepts within the document.

        Document Content:
        "{content}"
        
        Your structured response should include:
        - A summary of the scenario.
        - Potential risks based on the document.
        - Recommended actions.
        """
    )
    
    parser = StrOutputParser()
    scenario_chain = scenario_prompt | llm | parser
    
    analysis = scenario_chain.invoke({
        "scenario": request.scenario_text,
        "content": doc.content
    })
    
    return ScenarioResponse(scenario=request.scenario_text, analysis=analysis)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)