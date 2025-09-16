from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from .database import Base, engine

import os
from dotenv import load_dotenv


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Integer, default=1)
    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    analyses = relationship("Analysis", back_populates="document")

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    document = relationship("Document", back_populates="analyses")
    overall_risk_score = Column(Float)
    high_risk_clauses = Column(Text)  # JSON string
    simplified_summary = Column(Text)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Function to create all tables
def create_tables():
    try:
        Base.metadata.create_all(bind=engine) # Use the imported engine
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating database tables: {str(e)}")
        return False