from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import shutil
import os
import fitz
import pdfplumber
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
from models import SessionLocal, User, Document, Analysis
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash

app = FastAPI(
    title="LexiLens AI API",
    description="Production-Grade Legal Document Intelligence Platform API",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    existing_user = db.query(User).filter(User.email == "test@example.com").first()
    if not existing_user:
        hashed_password = get_password_hash("test123")
        test_user = User(email="test@example.com", hashed_password=hashed_password)
        db.add(test_user)
        db.commit()
        print("Default test user created")
    db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")

# Validate API key
if GEMINI_API_KEY == "your-api-key-here" or not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in environment variables!")
    print("Please set GEMINI_API_KEY in your .env file")
    llm = None
elif not GEMINI_API_KEY.startswith("AIza"):
    print("❌ ERROR: GEMINI_API_KEY appears to be invalid (should start with 'AIza')")
    print(f"Current key: {GEMINI_API_KEY}")
    llm = None
elif GEMINI_API_KEY != GEMINI_API_KEY.strip():
    print("❌ ERROR: GEMINI_API_KEY contains leading/trailing whitespace")
    print("Please remove any spaces from the API key in your .env file")
    llm = None
else:
    print(f"✅ GEMINI_API_KEY format looks correct: {GEMINI_API_KEY[:10]}...")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
        print("✅ LLM initialized successfully")
    except Exception as e:
        print(f"❌ ERROR initializing LLM: {str(e)}")
        if "API_KEY_INVALID" in str(e):
            print("💡 The API key is invalid. Please check:")
            print("   1. The key is copied correctly from Google AI Studio")
            print("   2. The key hasn't expired")
            print("   3. The key has the right permissions")
        llm = None

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"PyMuPDF failed: {str(e)}, trying pdfplumber...")
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e2:
            print(f"pdfplumber also failed: {str(e2)}")
            raise Exception(f"Could not extract text from PDF: {str(e)} / {str(e2)}")
    
    if not text.strip():
        raise Exception("PDF appears to be empty or contains no extractable text")
    
    return text

def analyze_document_with_ai(text):
    # Check if LLM is initialized
    if llm is None:
        return {
            "overall_risk_score": 0.5,
            "high_risk_clauses": [],
            "simplified_summary": "AI analysis is currently unavailable due to API key configuration issues. Please contact the administrator.",
            "processing_time": 0.0,
            "error": "GEMINI_API_KEY not configured properly"
        }
    
    try:
        # Refined prompt for legal risk classification
        risk_prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            Analyze the following legal document for risk. Identify clauses related to:
            - Termination
            - Payment terms
            - Liability
            - Intellectual property
            - Confidentiality
            - Dispute resolution

            For each identified clause, provide:
            - Clause text (quote directly)
            - Risk level (High, Medium, Low) based on potential impact
            - Confidence score (0-1)
            - Reason for risk level

            Also, calculate an overall risk score (0-1) for the document.

            Document text:
            {text}

            Output in JSON format with keys: overall_risk_score, clauses (list of dicts with clause, risk, confidence, reason)
            """
        )
        risk_chain = LLMChain(llm=llm, prompt=risk_prompt)
        risk_result_str = risk_chain.run(text=text)
        
        try:
            risk_result = json.loads(risk_result_str)
        except:
            risk_result = {"overall_risk_score": 0.5, "clauses": []}

        # Prompt for simplification
        simplify_prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            Simplify the following legal document into plain English. Focus on key obligations, rights, and risks.
            Use simple language and explain any legal terms.

            Document text:
            {text}

            Provide a concise simplified summary.
            """
        )
        simplify_chain = LLMChain(llm=llm, prompt=simplify_prompt)
        response = simplify_chain.invoke({"text": text})
        simplified = response["text"] if "text" in response else response["output_text"]
        import re

        simplified = (re.sub(r'\*{1,2}', '', simplified))

        return {
            "overall_risk_score": risk_result.get("overall_risk_score", 0.5),
            "high_risk_clauses": risk_result.get("clauses", []),
            "simplified_summary": simplified,
            "processing_time": 5.0
        }
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        return {
            "overall_risk_score": 0.5,
            "high_risk_clauses": [],
            "simplified_summary": "Analysis temporarily unavailable. Please try again later.",
            "processing_time": 0.0,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {"message": "Welcome to LexiLens AI API"}

@app.get("/health")
async def health_check():
    api_key_status = "configured" if llm is not None else "not_configured"
    return {
        "status": "healthy" if llm is not None else "degraded",
        "message": "LexiLens AI API is running",
        "api_key_status": api_key_status,
        "llm_available": llm is not None
    }

@app.get("/documents/{document_id}")
async def get_document(document_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get the latest analysis for this document
    analysis = db.query(Analysis).filter(Analysis.document_id == document_id).order_by(Analysis.created_at.desc()).first()
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "content": doc.content,
        "uploaded_at": doc.uploaded_at,
        "analysis": {
            "overall_risk_score": analysis.overall_risk_score if analysis else 0.5,
            "high_risk_clauses": json.loads(analysis.high_risk_clauses) if analysis else [],
            "simplified_summary": analysis.simplified_summary if analysis else "No analysis available",
            "processing_time": analysis.processing_time if analysis else 0.0
        } if analysis else None
    }

@app.post("/search")
async def search_documents(query: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user's documents
    docs = db.query(Document).filter(Document.owner_id == user.id).all()
    
    results = []
    for doc in docs:
        # Simple text search (can be improved with vector search)
        if query.lower() in doc.content.lower():
            # Use AI to provide context
            context_prompt = PromptTemplate(
                input_variables=["query", "content"],
                template="""
                Given the search query: "{query}"
                And the document content: {content}
                
                Provide a relevant snippet from the document that matches the query.
                """
            )
            context_chain = LLMChain(llm=llm, prompt=context_prompt)
            snippet = context_chain.run(query=query, content=doc.content[:1000])  # Limit content
            
            results.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "snippet": snippet
            })
    
    return {"query": query, "results": results}

@app.post("/scenario")
async def analyze_scenario(scenario: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user's recent documents
    docs = db.query(Document).filter(Document.owner_id == user.id).order_by(Document.uploaded_at.desc()).limit(3).all()
    
    combined_content = "\n".join([doc.content for doc in docs])
    
    scenario_prompt = PromptTemplate(
        input_variables=["scenario", "content"],
        template="""
        Analyze this legal scenario: "{scenario}"
        
        Based on the following document content, provide actionable advice and potential risks:
        {content}
        
        Structure your response as:
        - Summary of the scenario
        - Potential risks
        - Recommended actions
        - Relevant clauses from documents
        """
    )
    scenario_chain = LLMChain(llm=llm, prompt=scenario_prompt)
    analysis = scenario_chain.run(scenario=scenario, content=combined_content[:2000])  # Limit content
    
    return {"scenario": scenario, "analysis": analysis}

@app.post("/register")
async def register(email: str, password: str, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...), token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        text = extract_text_from_pdf(temp_path)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Save document to DB
        doc = Document(filename=file.filename, content=text, owner_id=user.id)
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
        
        os.remove(temp_path)
        
        return {**analysis_result, "document_id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Analysis endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
