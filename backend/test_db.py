#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from models import SessionLocal, User, Document, Analysis
from auth import get_password_hash

def test_database():
    """Test database functionality"""
    db = SessionLocal()
    try:
        # Check if test user exists
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            print("❌ Test user not found")
            return False

        print("✅ Test user found:", test_user.email)

        # Check documents
        documents = db.query(Document).filter(Document.owner_id == test_user.id).all()
        print(f"✅ Found {len(documents)} documents for test user")

        for doc in documents:
            print(f"  - Document: {doc.filename} (ID: {doc.id})")
            # Check analysis
            analysis = db.query(Analysis).filter(Analysis.document_id == doc.id).first()
            if analysis:
                print(f"    Analysis: Risk Score {analysis.overall_risk_score:.2f}")
            else:
                print("    No analysis found")

        print("✅ Database test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
