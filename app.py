import streamlit as st
import requests

# Set page config
st.set_page_config(
    page_title="LexiLens AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"
if "token" not in st.session_state:
    st.session_state.token = None
if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = {}  # Store documents by ID
if "current_document_id" not in st.session_state:
    st.session_state.current_document_id = None
if "db_synced" not in st.session_state:
    st.session_state.db_synced = False

def load_documents_from_db():
    """Load user's documents from database and sync with session state"""
    if not st.session_state.token:
        return
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get("http://localhost:8000/user/documents", headers=headers)
        
        if response.status_code == 200:
            db_docs = response.json()
            
            # Sync database documents with session state
            for db_doc in db_docs:
                doc_id = str(db_doc['id'])
                if doc_id not in st.session_state.uploaded_documents:
                    # Load document content and analysis from database
                    # For now, we'll store basic info and load content when needed
                    st.session_state.uploaded_documents[doc_id] = {
                        "filename": db_doc['filename'],
                        "content": None,  # Will be loaded when needed
                        "analysis": None,  # Will be loaded when needed
                        "uploaded_at": db_doc.get('uploaded_at', ''),
                        "from_db": True
                    }
            
            st.session_state.db_synced = True
    except Exception as e:
        st.error(f"Failed to load documents from database: {str(e)}")

def load_document_content(doc_id):
    """Load full document content and analysis from database when needed"""
    if doc_id not in st.session_state.uploaded_documents:
        return None
    
    doc_info = st.session_state.uploaded_documents[doc_id]
    
    # If we already have the content, return it
    if doc_info.get('content') is not None and doc_info.get('analysis') is not None:
        return doc_info
    
    # Otherwise, load it from database
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"http://localhost:8000/documents/{doc_id}", headers=headers)
        
        if response.status_code == 200:
            db_doc = response.json()
            doc_info['content'] = db_doc['content']
            doc_info['analysis'] = db_doc['analysis']
            doc_info['uploaded_at'] = db_doc['uploaded_at']
            return doc_info
        else:
            st.error(f"Failed to load document content: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Failed to load document content: {str(e)}")
        return None

def display_analysis_results(result, filename):
    """Display analysis results in a beautiful, user-friendly format"""
    
    # Overall Risk Score with color coding
    risk_score = result.get('overall_risk_score', 0)
    
    # Color coding for risk levels
    if risk_score < 0.3:
        risk_color = "🟢"
        risk_level = "Low Risk"
        risk_desc = "This document appears to have minimal risk factors."
        risk_class = "risk-low"
    elif risk_score < 0.7:
        risk_color = "🟡"
        risk_level = "Medium Risk"
        risk_desc = "This document has some risk factors that should be reviewed."
        risk_class = "risk-medium"
    else:
        risk_color = "🔴"
        risk_level = "High Risk"
        risk_desc = "This document contains significant risk factors requiring attention."
        risk_class = "risk-high"
    
    st.markdown("---")
    st.subheader("📊 Analysis Results")
    
    # Risk Score Card with custom styling
    st.markdown(f"""
    <div class="analysis-card">
        <h3 style="margin: 0; color: white;">{risk_color} {risk_level}</h3>
        <p style="margin: 0.5rem 0; opacity: 0.9;">{risk_desc}</p>
        <div style="display: flex; justify-content: space-around; margin-top: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #fbbf24;">{risk_score:.2f}</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Risk Score</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #60a5fa;">{result.get('processing_time', 0):.1f}s</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Processing Time</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #ef4444;">{len(result.get('high_risk_clauses', []))}</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">High Risk Clauses</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Simplified Summary with custom styling
    st.subheader("📝 Simplified Summary")
    summary = result.get('simplified_summary', 'No summary available')
    
    st.write(summary)
  
    
    # High Risk Clauses
    high_risk_clauses = result.get('high_risk_clauses', [])
    if high_risk_clauses:
        st.subheader("⚠️ High Risk Clauses")
        
        for i, clause in enumerate(high_risk_clauses, 1):
            risk_level = clause.get('risk', 'Unknown')
            
            # Color coding for clause risk
            if risk_level.lower() == 'high':
                clause_color = "🔴"
                clause_bg = "#fee2e2"
                clause_border = "#fca5a5"
            elif risk_level.lower() == 'medium':
                clause_color = "🟡"
                clause_bg = "#fef3c7"
                clause_border = "#fcd34d"
            else:
                clause_color = "🟢"
                clause_bg = "#d1fae5"
                clause_border = "#6ee7b7"
            
            with st.expander(f"{clause_color} Risk Clause #{i} - {risk_level} Risk"):
                st.markdown(f"""
                <div style="background-color: {clause_bg}; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid {clause_border}; margin-bottom: 1rem;">
                    <strong>📄 Clause Text:</strong><br>
                    {clause.get('clause', 'No clause text available')}
                </div>
                <div style="background-color: #f1f5f9; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <strong>💡 Reason:</strong><br>
                    {clause.get('reason', 'No reason provided')}
                </div>
                <div style="background-color: #e2e8f0; padding: 1rem; border-radius: 0.5rem;">
                    <strong>🎯 Confidence:</strong> {clause.get('confidence', 'N/A')}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ No high-risk clauses detected in this document!")
    
    # Document Info
    st.subheader("📄 Document Information")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <strong>📁 Filename</strong><br>
            {filename}
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <strong>🆔 Document ID</strong><br>
            {result.get('document_id', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔍 Search This Document", type="secondary"):
            st.session_state.page = "search"
            st.rerun()
    with col2:
        if st.button("🎭 Analyze Scenarios", type="secondary"):
            st.session_state.page = "scenarios"
            st.rerun()
    with col3:
        if st.button("📊 View Dashboard", type="primary"):
            st.session_state.page = "dashboard"
            st.rerun()

    # Sidebar navigation
    st.sidebar.title("⚖️ LexiLens AI")
    if st.sidebar.button("Home"):
        st.session_state.page = "home"
    if st.sidebar.button("Login"):
        st.session_state.page = "login"
    if st.session_state.token:
        if st.sidebar.button("Dashboard"):
            st.session_state.page = "dashboard"
        if st.sidebar.button("Upload & Analyze"):
            st.session_state.page = "upload"
        if st.sidebar.button("Search & Explore"):
            st.session_state.page = "search"
        if st.sidebar.button("What-If Scenarios"):
            st.session_state.page = "scenarios"
        if st.sidebar.button("Logout"):
            st.session_state.token = None
            st.session_state.uploaded_documents = {}  # Clear uploaded documents
            st.session_state.current_document_id = None
            st.session_state.db_synced = False  # Reset database sync flag
            st.session_state.page = "home"
            st.rerun()
        
        # Show current document status in sidebar
        if st.session_state.uploaded_documents:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📄 Your Documents")
            for doc_id, doc_info in st.session_state.uploaded_documents.items():
                if st.sidebar.button(f"{doc_info['filename'][:20]}...", key=f"sidebar_{doc_id}"):
                    st.session_state.current_document_id = doc_id
                    st.session_state.page = "upload"
                    st.rerun()
            st.sidebar.metric("Total Documents", len(st.session_state.uploaded_documents))# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #3b82f6;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #e2e8f0;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: #1e293b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
        text-align: center;
    }
    .dashboard-card {
        background-color: #1e293b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
    }
    .analysis-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .risk-low {
        background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .risk-medium {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .risk-high {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1e293b;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem;
        border: 1px solid #334155;
    }
    .summary-box {
        background-color: #0f172a;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Page routing
if st.session_state.page == "home":
    # Landing Page
    st.markdown('<div class="main-header">⚖️ LexiLens AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">From Legal Chaos to Crystal Clarity</div>', unsafe_allow_html=True)
    st.markdown("""
    The enterprise-grade AI platform that deconstructs, classifies, and simplifies your contracts.  
    Use our dashboard or integrate directly with our API.
    """)
    if st.button("Get Started"):
        st.session_state.page = "login"

    # Features Section
    st.header("Features")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>Intelligent Deconstruction</h3>
            <p>Go beyond simple text extraction. Our engine understands multi-column layouts, tables, and complex structures.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>Advanced Risk Classification</h3>
            <p>Leverage an industry-specific AI model that detects high-risk clauses and assigns confidence scores.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>Context-Aware Simplification</h3>
            <p>Instantly translate dense legal jargon into plain English with our glossary of 500+ terms.</p>
        </div>
        """, unsafe_allow_html=True)

    # More features
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("""
        <div class="feature-card">
            <h3>Semantic Search Engine</h3>
            <p>Find what you need instantly with hybrid search combining keywords and semantic understanding.</p>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown("""
        <div class="feature-card">
            <h3>What-If Scenario Analysis</h3>
            <p>Use our conversational AI to ask complex questions and receive actionable guidance.</p>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.markdown("""
        <div class="feature-card">
            <h3>Developer-First API</h3>
            <p>Integrate the full power of LexiLens into your own applications with our REST API.</p>
        </div>
        """, unsafe_allow_html=True)

    # Pricing Section
    st.header("Pricing")
    st.markdown("""
    - **Free:** For individuals (3 documents/month, standard analysis)
    - **Pro:** For professionals (Unlimited documents, advanced analysis, search, scenario simulation)
    - **Business:** For teams (All Pro features + API Access, professional reporting, multi-user accounts)
    """)

elif st.session_state.page == "login":
    # Login Page
    st.header("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        response = requests.post("http://localhost:8000/token", data={"username": email, "password": password})
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.success("Logged in successfully!")
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Invalid credentials")
    if st.button("Register"):
        response = requests.post("http://localhost:8000/register", params={"email": email, "password": password})
        if response.status_code == 200:
            st.success("Registered successfully! Please login.")
        else:
            st.error("Registration failed")

elif st.session_state.page == "dashboard":
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # Load documents from database if not already synced
        if not st.session_state.db_synced:
            with st.spinner("Loading your documents..."):
                load_documents_from_db()
        
        # Dashboard Home
        st.header("Dashboard")
        st.markdown("Welcome to your LexiLens AI dashboard.")
        
        # Show documents (from both session and database)
        total_docs = len(st.session_state.uploaded_documents)
        if total_docs > 0:
            st.metric("Total Documents", total_docs)
            
            # Recent Documents
            st.subheader("Your Documents")
            for doc_id, doc_info in list(st.session_state.uploaded_documents.items())[-5:]:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    source_icon = "💾" if doc_info.get('from_db') else "📤"
                    st.write(f"{source_icon} {doc_info['filename']}")
                with col2:
                    if doc_info.get('analysis'):
                        risk_score = doc_info['analysis'].get('overall_risk_score', 0)
                        st.write(f"Risk: {risk_score:.2f}")
                    else:
                        st.write("Risk: N/A")
                with col3:
                    if st.button("View", key=f"view_{doc_id}"):
                        st.session_state.current_document_id = doc_id
                        st.session_state.page = "upload"
                        st.rerun()
        else:
            st.metric("Total Documents", "0")
            st.info("No documents uploaded yet. Go to **Upload & Analyze** to get started.")
        
        # Mock other metrics
        st.metric("High-Risk Clauses Detected", "5")
        st.metric("Reports Generated", "3")
        
        # Risk Distribution Chart
        st.subheader("Risk Distribution")
        st.bar_chart({"Low": 3, "Medium": 5, "High": 4})

elif st.session_state.page == "upload":
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # Upload & Analyze
        st.header("Upload & Analyze Document")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        if uploaded_file is not None:
            st.write("File uploaded:", uploaded_file.name)
            if st.button("Analyze Document"):
                with st.spinner("🔍 Extracting text from PDF..."):
                    # Simulate text extraction time
                    import time
                    time.sleep(1)
                    
                with st.spinner("🤖 AI analyzing document for risks..."):
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": uploaded_file.getvalue()}
                    response = requests.post("http://localhost:8000/analyze", files=files, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Analysis complete!")
                        
                        # Store document in session state
                        doc_id = result.get("document_id")
                        st.session_state.uploaded_documents[doc_id] = {
                            "filename": uploaded_file.name,
                            "content": uploaded_file.getvalue(),
                            "analysis": result,
                            "uploaded_at": str(result.get("processing_time", 0))
                        }
                        st.session_state.current_document_id = doc_id
                        
                        # Display beautiful analysis results
                        display_analysis_results(result, uploaded_file.name)
                    else:
                        st.error("❌ Analysis failed. Please try again.")
        
        # Show current document analysis if one is selected
        if st.session_state.current_document_id and st.session_state.current_document_id in st.session_state.uploaded_documents:
            current_doc = st.session_state.uploaded_documents[st.session_state.current_document_id]
            
            analysis = current_doc.get('analysis', {})
            if analysis:
                # Display beautiful analysis results for current document
                display_analysis_results(analysis, current_doc['filename'])
            else:
                st.info("Document uploaded but not yet analyzed.")
        
        # Show previously uploaded documents
        if st.session_state.uploaded_documents:
            st.subheader("Your Documents")
            for doc_id, doc_info in st.session_state.uploaded_documents.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    if st.button(f"📄 {doc_info['filename']}", key=f"select_{doc_id}"):
                        st.session_state.current_document_id = doc_id
                        st.rerun()
                with col2:
                    st.write(f"Risk: {doc_info['analysis'].get('overall_risk_score', 0):.2f}")
                with col3:
                    if st.button("🗑️", key=f"delete_{doc_id}"):
                        del st.session_state.uploaded_documents[doc_id]
                        if st.session_state.current_document_id == doc_id:
                            st.session_state.current_document_id = None
                        st.rerun()
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # Search & Explore
        st.header("Search & Explore")
        
        # Document selector
        if st.session_state.uploaded_documents:
            st.subheader("📋 Select Document")
            doc_options = ["Select a document..."] + [f"{doc_id}: {info['filename']}" for doc_id, info in st.session_state.uploaded_documents.items()]
            selected_doc = st.selectbox("Choose document to search in:", doc_options, key="search_doc_selector")
            
            # Quick document switcher
            if len(st.session_state.uploaded_documents) > 1:
                st.write("**Quick Switch:**")
                cols = st.columns(min(len(st.session_state.uploaded_documents), 4))
                for i, (doc_id, doc_info) in enumerate(st.session_state.uploaded_documents.items()):
                    if i < 4:
                        with cols[i]:
                            if st.button(f"📄\n{doc_info['filename'][:15]}...", key=f"quick_search_{doc_id}"):
                                st.session_state.page = "search"
                                # This will trigger a rerun and update the selectbox
                                st.rerun()
            
            if selected_doc != "Select a document...":
                doc_id = selected_doc.split(": ")[0]
                doc_info = st.session_state.uploaded_documents[doc_id]
                
                # Load full content if from database
                if doc_info.get('from_db') and doc_info.get('content') is None:
                    with st.spinner("Loading document content..."):
                        load_document_content(doc_id)
                        doc_info = st.session_state.uploaded_documents[doc_id]
                
                # Show selected document info
                st.success(f"📄 Selected: {doc_info['filename']}")
                col1, col2 = st.columns(2)
                with col1:
                    risk_score = doc_info['analysis'].get('overall_risk_score', 0) if doc_info.get('analysis') else 0
                    st.metric("Risk Score", f"{risk_score:.2f}")
                with col2:
                    high_risk_count = len(doc_info['analysis'].get('high_risk_clauses', [])) if doc_info.get('analysis') else 0
                    st.metric("High Risk Clauses", high_risk_count)
                
                st.subheader(f"🔍 Searching in: {doc_info['filename']}")
                query = st.text_input("Enter search query", placeholder="e.g., termination, payment terms, liability")
                
                if st.button("🔎 Search Document", type="primary"):
                    if query:
                        with st.spinner("Searching document..."):
                            # Use backend search endpoint
                            headers = {"Authorization": f"Bearer {st.session_state.token}"}
                            search_data = {"query": query}
                            response = requests.post("http://localhost:8000/search", json=search_data, headers=headers)
                            
                            if response.status_code == 200:
                                search_results = response.json()
                                results = search_results.get("results", [])
                                st.success(f"✅ Found {len(results)} results for '{query}'")
                                
                                if results:
                                    for result in results:
                                        with st.expander(f"📄 {result.get('filename', 'Document')} - Match Found"):
                                            st.write("**📝 Relevant Snippet:**")
                                            st.write(result.get('snippet', 'No snippet available'))
                                            st.write("---")
                                            if st.button("👁️ View Full Document", key=f"view_doc_{result.get('document_id')}"):
                                                st.session_state.current_document_id = result.get('document_id')
                                                st.session_state.page = "upload"
                                                st.rerun()
                                else:
                                    st.info("No matches found. Try different keywords or check spelling.")
                            else:
                                st.error("Search failed. Please try again.")
                    else:
                        st.warning("Please enter a search query")
            else:
                st.info("👆 Please select a document from the dropdown above to start searching")
        else:
            st.warning("📤 No documents uploaded yet.")
            st.info("Go to **Upload & Analyze** page to upload your first document")
            if st.button("📤 Go to Upload Page"):
                st.session_state.page = "upload"
                st.rerun()

elif st.session_state.page == "scenarios":
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # What-If Scenarios
        st.header("What-If Scenarios")
        
        # Document selector
        if st.session_state.uploaded_documents:
            st.subheader("📋 Select Document")
            doc_options = ["Select a document..."] + [f"{doc_id}: {info['filename']}" for doc_id, info in st.session_state.uploaded_documents.items()]
            selected_doc = st.selectbox("Choose document for scenario analysis:", doc_options, key="scenario_doc_selector")
            
            # Quick document switcher
            if len(st.session_state.uploaded_documents) > 1:
                st.write("**Quick Switch:**")
                cols = st.columns(min(len(st.session_state.uploaded_documents), 4))
                for i, (doc_id, doc_info) in enumerate(st.session_state.uploaded_documents.items()):
                    if i < 4:
                        with cols[i]:
                            if st.button(f"📄\n{doc_info['filename'][:15]}...", key=f"quick_scenario_{doc_id}"):
                                st.session_state.page = "scenarios"
                                # This will trigger a rerun and update the selectbox
                                st.rerun()
            
            if selected_doc != "Select a document...":
                doc_id = selected_doc.split(": ")[0]
                doc_info = st.session_state.uploaded_documents[doc_id]
                
                # Load full content if from database
                if doc_info.get('from_db') and doc_info.get('content') is None:
                    with st.spinner("Loading document content..."):
                        load_document_content(doc_id)
                        doc_info = st.session_state.uploaded_documents[doc_id]
                
                # Show selected document info
                st.success(f"📄 Selected: {doc_info['filename']}")
                col1, col2 = st.columns(2)
                with col1:
                    risk_score = doc_info['analysis'].get('overall_risk_score', 0) if doc_info.get('analysis') else 0
                    st.metric("Risk Score", f"{risk_score:.2f}")
                with col2:
                    high_risk_count = len(doc_info['analysis'].get('high_risk_clauses', [])) if doc_info.get('analysis') else 0
                    st.metric("High Risk Clauses", high_risk_count)
                
                st.subheader(f"🎭 Analyzing scenarios for: {doc_info['filename']}")
                scenario = st.text_area("Describe your what-if scenario", 
                                      placeholder="e.g., What if the payment terms change? What if we terminate the contract early? What if there's a breach of confidentiality?",
                                      height=100)
                
                if st.button("🎭 Analyze Scenario", type="primary"):
                    if scenario:
                        with st.spinner("Analyzing scenario..."):
                            # Use backend scenario endpoint
                            headers = {"Authorization": f"Bearer {st.session_state.token}"}
                            scenario_data = {"scenario": scenario}
                            response = requests.post("http://localhost:8000/scenario", json=scenario_data, headers=headers)
                            
                            if response.status_code == 200:
                                scenario_result = response.json()
                                st.success("✅ Scenario analysis complete!")
                                
                                st.subheader("📊 Scenario Analysis Results")
                                st.write("**Your Scenario:**", scenario_result.get("scenario", scenario))
                                st.write("**🤖 AI Analysis:**")
                                st.write(scenario_result.get("analysis", "Analysis not available"))
                                
                                # Show relevant document information
                                st.subheader("📋 Based on Your Document")
                                risk_clauses = doc_info.get('analysis', {}).get('high_risk_clauses', [])
                                if risk_clauses:
                                    st.write("**⚠️ Relevant Risk Considerations:**")
                                    for i, clause in enumerate(risk_clauses[:3], 1):
                                        with st.expander(f"Risk #{i}: {clause.get('risk', 'Unknown')} Level"):
                                            st.write(f"**Clause:** {clause.get('clause', 'Unknown clause')}")
                                            st.write(f"**Reason:** {clause.get('reason', 'No reason provided')}")
                                            st.write(f"**Confidence:** {clause.get('confidence', 'N/A')}")
                                else:
                                    st.info("No high-risk clauses identified in this document")
                            else:
                                st.error("❌ Scenario analysis failed. Please try again.")
                    else:
                        st.warning("⚠️ Please describe your scenario")
            else:
                st.info("👆 Please select a document from the dropdown above to start scenario analysis")
        else:
            st.warning("📤 No documents uploaded yet.")
            st.info("Go to **Upload & Analyze** page to upload your first document")
            if st.button("📤 Go to Upload Page"):
                st.session_state.page = "upload"
                st.rerun()

# Footer
st.markdown("---")
st.markdown("© 2025 LexiLens AI. All rights reserved.")
