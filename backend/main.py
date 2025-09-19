from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form, BackgroundTasks
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

# Local Imports
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
else:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
        print("✅ LLM initialized successfully")
    except Exception as e:
        print(f"❌ ERROR initializing LLM: {str(e)}")
        llm = None

# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting LexiLens AI API...")
    if not create_tables():
        print("❌ Failed to create database tables.")
    else:
        print("✅ Database tables ready")

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "test@example.com").first():
            hashed_password = get_password_hash("test123")
            test_user = User(email="test@example.com", hashed_password=hashed_password)
            db.add(test_user)
            db.commit()
            print("✅ Default test user created (test@example.com / test123)")
    finally:
        db.close()
    yield
    print("👋 Shutting down LexiLens AI API...")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="LexiLens AI API",
    description="Production-Grade Legal Document Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# --- Pydantic Schemas ---
class DocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    uploaded_at: datetime
    class Config: from_attributes = True

class DocumentDetail(DocumentOut):
    content: str
    analysis: Optional[dict] = None

class ScenarioRequest(BaseModel):
    scenario_text: str

class ScenarioResponse(BaseModel):
    scenario: str
    analysis: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class AnalyzeImmediateResponse(BaseModel):
    message: str
    document_id: int
    filename: str

class RegisterResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str
    message: str
    api_key_status: str
    database: str
    llm_available: bool

class DocumentQARequest(BaseModel):
    question: str

class DocumentQAResponse(BaseModel):
    question: str
    answer: str
    document_id: int

class NegotiateRequest(BaseModel):
    clause_text: str
    risk_level: str

class NegotiateResponse(BaseModel):
    original_clause: str
    suggestions: List[str]

class SuggestionResponse(BaseModel):
    qa_suggestions: List[str]
    scenario_suggestions: List[str]

# --- Helper Functions ---
def extract_text_from_pdf(file_path: str) -> str:
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
            raise IOError(f"Could not extract text from PDF: {e} / {e2}")
    if not text.strip():
        raise ValueError("PDF appears to be empty or contains no extractable text")
    return text

def analyze_document_with_ai(text: str) -> dict:
    if llm is None:
        return {"error": "GEMINI_API_KEY not configured properly"}
    try:
        parser = StrOutputParser()
        risk_prompt = PromptTemplate.from_template(
            """Analyze the following legal document for risk. Identify clauses related to Termination, Payment terms, Liability, Intellectual property, Confidentiality, and Dispute resolution. For each, provide: 'clause' (quoted text), 'risk' (High, Medium, or Low), 'confidence' (0-1 score), and 'reason'. Also, calculate an 'overall_risk_score' (0-1). Document text: {text}. Output ONLY a valid JSON object with keys: 'overall_risk_score', 'clauses' (a list of dictionaries)."""
        )
        risk_chain = risk_prompt | llm | parser
        risk_result_str = risk_chain.invoke({"text": text})
        risk_result = json.loads(risk_result_str.strip().replace("```json", "").replace("```", ""))

        simplify_prompt = PromptTemplate.from_template(
            """Simplify the following legal document into plain English. Focus on key obligations, rights, and risks. Document text: {text}. Provide a concise simplified summary."""
        )
        simplify_chain = simplify_prompt | llm | parser
        simplified = simplify_chain.invoke({"text": text})
        
        return {
            "overall_risk_score": risk_result.get("overall_risk_score", 0.5),
            "high_risk_clauses": risk_result.get("clauses", []),
            "simplified_summary": simplified.strip(),
            "processing_time": 5.0
        }
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        raise e

# --- Background Task Worker ---
def run_ai_analysis_and_save(doc_id: int, db: Session):
    print(f"🔬 Starting background analysis for document ID: {doc_id}")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        print(f"❌ Could not find document ID {doc_id} for background analysis.")
        db.close()
        return

    try:
        analysis_result = analyze_document_with_ai(doc.content)
        analysis = Analysis(
            document_id=doc.id,
            overall_risk_score=analysis_result.get("overall_risk_score", 0.0),
            high_risk_clauses=json.dumps(analysis_result.get("high_risk_clauses", [])),
            simplified_summary=analysis_result.get("simplified_summary", ""),
            processing_time=analysis_result.get("processing_time", 0.0)
        )
        db.add(analysis)
        db.commit()
        print(f"✅ Background analysis for document ID {doc_id} complete and saved.")
    except Exception as e:
        print(f"❌ Background analysis for document ID {doc_id} failed: {str(e)}")
    finally:
        db.close()

# --- API Endpoints ---
@app.post("/analyze", response_model=AnalyzeImmediateResponse, tags=["Analysis"])
async def analyze_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        text = extract_text_from_pdf(temp_path)
        file_title = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").title()
        
        doc = Document(
            title=file_title,
            filename=file.filename,
            content=text,
            owner_id=current_user.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        background_tasks.add_task(run_ai_analysis_and_save, doc.id, SessionLocal())
        
        return AnalyzeImmediateResponse(
            message="Document uploaded successfully. Analysis has started in the background.",
            document_id=doc.id,
            filename=file.filename
        )
    except (IOError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/scenario/{document_id}", response_model=ScenarioResponse, tags=["Analysis"])
async def analyze_scenario_for_document(
    document_id: int,
    request: ScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    scenario_prompt = PromptTemplate.from_template(
        """Analyze this legal scenario: "{scenario}"\n\nBased ONLY on the following document content, provide actionable advice and potential risks.\n\nDocument Content:\n"{content}"\n\nYour structured response should include:\n- A summary of the scenario.\n- Potential risks based on the document.\n- Recommended actions."""
    )
    parser = StrOutputParser()
    scenario_chain = scenario_prompt | llm | parser
    analysis = scenario_chain.invoke({"scenario": request.scenario_text, "content": doc.content})
    return ScenarioResponse(scenario=request.scenario_text, analysis=analysis)

# ... (Keep all your other endpoints: /register, /token, /user/documents, etc. They are correct)
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
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
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

@app.get("/user/documents", response_model=List[DocumentOut], tags=["Documents"])
async def get_user_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.owner_id == current_user.id).order_by(Document.uploaded_at.desc()).all()

@app.post("/document/{document_id}/query", response_model=DocumentQAResponse, tags=["Analysis"])
async def query_document(
    document_id: int,
    request: DocumentQARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers a specific question based on the content of a single document.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    qa_prompt = PromptTemplate.from_template(
        """
        You are an AI assistant specialized in legal document analysis.
        Answer the following question based ONLY on the provided document content.
        If the answer is not in the document, state that clearly. Be concise and precise.

        Question: "{question}"
        
        Document Content:
        "{content}"
        """
    )
    
    parser = StrOutputParser()
    qa_chain = qa_prompt | llm | parser
    
    answer = qa_chain.invoke({
        "question": request.question,
        "content": doc.content
    })
    
    return DocumentQAResponse(
        question=request.question,
        answer=answer,
        document_id=document_id
    )

@app.post("/negotiate-clause", response_model=NegotiateResponse, tags=["Analysis"])
async def negotiate_clause(
    request: NegotiateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generates fairer, alternative wording for a high-risk legal clause.
    """
    if not llm:
        raise HTTPException(status_code=503, detail="AI service is unavailable.")

    negotiate_prompt = PromptTemplate.from_template(
        """
        You are an AI assistant skilled in legal contract negotiation.
        Your user has identified a clause with a '{risk_level}' risk level.
        Your task is to rewrite this clause to be more fair and balanced, while preserving the original intent where possible.

        Original Clause:
        "{clause_text}"

        Generate 2-3 distinct, alternative versions of this clause that are more favorable to the user.
        Each suggestion should be a complete, professionally worded clause.
        
        Return ONLY a JSON object with a single key "suggestions" which is a list of the suggested clause strings.
        Example: {{"suggestions": ["First suggested clause...", "Second suggested clause..."]}}
        """
    )
    
    parser = StrOutputParser()
    negotiate_chain = negotiate_prompt | llm | parser
    
    try:
        response_str = negotiate_chain.invoke({
            "risk_level": request.risk_level,
            "clause_text": request.clause_text
        })
        # Clean and parse the JSON output from the LLM
        response_json = json.loads(response_str.strip().replace("```json", "").replace("```", ""))
        suggestions = response_json.get("suggestions", ["Could not generate suggestions."])
        
        return NegotiateResponse(
            original_clause=request.clause_text,
            suggestions=suggestions
        )
    except Exception as e:
        print(f"Negotiation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate negotiation suggestions.")

@app.delete("/documents/{document_id}", status_code=status.HTTP_200_OK, tags=["Documents"])
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a document and all its associated analyses for the authenticated user.
    """
    # Find the document to ensure it belongs to the current user
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete associated analyses first to maintain data integrity
    db.query(Analysis).filter(Analysis.document_id == document_id).delete()
    
    # Now delete the document itself
    db.delete(doc)
    db.commit()
    
    return {"message": "Document and its analyses deleted successfully"}

@app.get("/documents/{document_id}/suggestions", response_model=SuggestionResponse, tags=["Analysis"])
async def get_suggestions_for_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates relevant Q&A and What-If scenario questions for a document.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    suggestion_prompt = PromptTemplate.from_template(
        """
        You are an AI assistant analyzing a legal document. Your task is to generate insightful questions a user might have.
        Based on the following document content, generate two lists of questions:
        1.  `qa_suggestions`: Three questions that can be answered directly from the text (e.g., "What is the termination notice period?").
        2.  `scenario_suggestions`: Three hypothetical "what-if" questions (e.g., "What happens if a payment is missed?").

        Document Content (first 2000 characters):
        "{content}"

        Return ONLY a valid JSON object with two keys: "qa_suggestions" and "scenario_suggestions".
        Example: {{"qa_suggestions": ["...", "..."], "scenario_suggestions": ["...", "..."]}}
        """
    )
    
    parser = StrOutputParser()
    suggestion_chain = suggestion_prompt | llm | parser
    
    try:
        # Limit content to keep the prompt efficient
        content_snippet = doc.content[:2000]
        response_str = suggestion_chain.invoke({"content": content_snippet})
        response_json = json.loads(response_str.strip().replace("```json", "").replace("```", ""))
        
        return SuggestionResponse(
            qa_suggestions=response_json.get("qa_suggestions", []),
            scenario_suggestions=response_json.get("scenario_suggestions", [])
        )
    except Exception as e:
        print(f"Suggestion generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate suggestions.")


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)