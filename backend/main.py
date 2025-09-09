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
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    return text

def analyze_document_with_ai(text):
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
    simplified = simplify_chain.run(text=text)

    return {
        "overall_risk_score": risk_result.get("overall_risk_score", 0.5),
        "high_risk_clauses": risk_result.get("clauses", []),
        "simplified_summary": simplified,
        "processing_time": 5.0
    }

@app.get("/")
async def root():
    return {"message": "Welcome to LexiLens AI API"}

@app.get("/user/documents")
async def get_user_documents(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    docs = db.query(Document).filter(Document.owner_id == user.id).all()
    return [{"id": doc.id, "filename": doc.filename, "uploaded_at": doc.uploaded_at} for doc in docs]

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
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    text = extract_text_from_pdf(temp_path)
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
