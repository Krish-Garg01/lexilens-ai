import streamlit as st
import requests
import time
import os

from dotenv import load_dotenv
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# --- Page Configuration ---
st.set_page_config(
    page_title="LexiLens AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "token" not in st.session_state:
    st.session_state.token = None
if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = {}
if "current_document_id" not in st.session_state:
    st.session_state.current_document_id = None

# --- Custom CSS for modern look ---
st.markdown("""
<style>
    /* General Styles */
    .stApp {
        background-color: #0f172a;
    }
    .main-container {
        max-width: 1200px;
        margin: auto;
        padding: 2rem;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #e2e8f0;
    }
    .stButton>button {
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
    }
    
    /* Hero Section */
    .hero-title {
        font-size: 3.5rem;
        font-weight: bold;
        line-height: 1.2;
        color: #ffffff;
    }
    .hero-subtitle {
        font-size: 1.25rem;
        color: #94a3b8;
        margin-top: 1rem;
        margin-bottom: 2rem;
    }

    /* Feature & Dashboard Cards */
    .card {
        background-color: #1e293b;
        padding: 2rem;
        border-radius: 0.75rem;
        text-align: center;
        border: 1px solid #334155;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    .card-icon {
        font-size: 3rem;
    }
    .card-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 1rem;
        color: #ffffff;
    }
    .card-description {
        color: #94a3b8;
        margin-top: 0.5rem;
    }
    
    /* Dashboard Specific */
    .dashboard-metric {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3b82f6; /* Accent color */
    }
    .dashboard-doc-list {
        background-color: #1e293b;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Answer Box */
    .answer-box {
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# --- API Communication Functions ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def fetch_user_documents():
    if not st.session_state.token: return
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/user/documents", headers=headers)
        if response.status_code == 200:
            st.session_state.uploaded_documents = {}
            for doc in response.json():
                doc_id = str(doc['id'])
                st.session_state.uploaded_documents[doc_id] = {
                    "title": doc.get('title', doc['filename']),
                    "filename": doc['filename'],
                    "uploaded_at": doc.get('uploaded_at', ''),
                    "analysis": None
                }
    except Exception as e: print(f"Error fetching documents: {e}")

def load_full_document_analysis(doc_id):
    if not st.session_state.token or not doc_id: return
    try:
        with st.spinner("Loading analysis..."):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.get(f"{BACKEND_URL}/documents/{doc_id}", headers=headers)
            if response.status_code == 200:
                full_doc_data = response.json()
                st.session_state.uploaded_documents[doc_id]['analysis'] = full_doc_data.get('analysis')
    except Exception as e: st.error(f"An error occurred: {e}")

# --- UI Component Functions ---
def display_analysis_results(analysis_result, title):
    if not analysis_result:
        st.warning("Analysis for this document is not available or still processing.")
        return
    st.subheader(f"📊 Analysis for: {title}")
    risk_score = analysis_result.get('overall_risk_score', 0.0)
    if risk_score is None: risk_score = 0.0
    
    if risk_score <= 0.3: delta_color, level = "inverse", "Low Risk"
    elif risk_score <= 0.7: delta_color, level = "normal", "Medium Risk"
    else: delta_color, level = "inverse", "High Risk"
    st.metric(label="Overall Risk Score", value=f"{risk_score:.2f}", delta=level, delta_color=delta_color)
    
    with st.expander("📝 Simplified Summary", expanded=True):
        st.write(analysis_result.get('simplified_summary', 'No summary provided.'))
        
    st.subheader("⚠️ High-Risk Clauses")
    high_risk_clauses = analysis_result.get('high_risk_clauses', [])
    
    if high_risk_clauses:
        for i, clause in enumerate(high_risk_clauses):
            with st.container(border=True):
                st.markdown(f"**Clause {i+1}:** {clause.get('clause', 'N/A')}")
                st.info(f"**Reason:** {clause.get('reason', 'N/A')}")
                st.progress(clause.get('confidence', 0.0), text=f"Confidence: {clause.get('confidence', 0.0):.0%}")
                
                if st.button("✍️ Suggest Alternatives", key=f"negotiate_{i}"):
                    with st.spinner("AI is drafting negotiation suggestions..."):
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        payload = {"clause_text": clause.get('clause', ''), "risk_level": clause.get('risk', 'High')}
                        response = requests.post(f"{BACKEND_URL}/negotiate-clause", json=payload, headers=headers)
                        if response.status_code == 200:
                            suggestions = response.json().get("suggestions", [])
                            st.success("Here are some fairer alternatives:")
                            for suggestion in suggestions:
                                st.code(suggestion, language="text")
                        else:
                            st.error(f"Could not get suggestions: {response.text}")
    else:
        st.success("No high-risk clauses were detected.")

def fetch_suggestions(doc_id):
    """Fetches AI-generated question suggestions for a document."""
    if not st.session_state.token or not doc_id:
        return
    try:
        with st.spinner("Generating suggestions..."):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.get(f"{BACKEND_URL}/documents/{doc_id}/suggestions", headers=headers)
            if response.status_code == 200:
                st.session_state.suggestions = response.json()
                st.session_state.last_suggestion_doc_id = doc_id
            else:
                st.session_state.suggestions = None
    except Exception as e:
        print(f"Error fetching suggestions: {e}")
        st.session_state.suggestions = None
# --- Page Routing ---
with st.sidebar:
    st.title("⚖️ LexiLens AI")
    if st.button("Home", use_container_width=True): st.session_state.page = "home"
    if not st.session_state.token:
        if st.button("Login / Register", use_container_width=True): st.session_state.page = "login"
    if st.session_state.token:
        if st.button("Dashboard", use_container_width=True): st.session_state.page = "dashboard"
        if st.button("Upload & Analyze", use_container_width=True): st.session_state.page = "upload"
        if st.button("Search / Q&A", use_container_width=True): st.session_state.page = "search"
        if st.button("What-If Scenarios", use_container_width=True): st.session_state.page = "scenarios"
        if st.button("Logout", use_container_width=True):
            st.session_state.clear(); st.session_state.page = "home"; st.rerun()

# --- Main Page Content ---
if st.session_state.page == "home":
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Hero Section
    st.title("⚖️ LexiLens AI")
    st.markdown('<p class="hero-title">From Legal Chaos to Crystal Clarity.</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">LexiLens AI deconstructs, classifies, and simplifies your contracts, empowering you to sign with confidence.</p>', unsafe_allow_html=True)
    if st.button("Get Started for Free", type="primary", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Why Choose Us Section
    st.header("Why Choose LexiLens AI?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="card"><div class="card-icon">⚡️</div><div class="card-title">Instant Clarity</div><p class="card-description">Go from a 50-page legal document to a simple, actionable summary in seconds, not hours.</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="card"><div class="card-icon">🛡️</div><div class="card-title">Risk Mitigation</div><p class="card-description">Our AI flags ambiguous, unfair, or high-risk clauses before they become a problem.</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="card"><div class="card-icon">🤝</div><div class="card-title">Empowered Negotiation</div><p class="card-description">Use our AI-powered suggestions to negotiate fairer terms and protect your interests.</p></div>""", unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Features Section
    st.header("Our Key Features")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="card"><div class="card-icon">🚨</div><div class="card-title">Advanced Risk Detection</div><p class="card-description">Leverage an AI model that detects high-risk clauses and assigns confidence scores.</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="card"><div class="card-icon">💡</div><div class="card-title">AI-Powered Simplification</div><p class="card-description">Instantly translate dense legal jargon into plain, easy-to-understand English.</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="card"><div class="card-icon">❓</div><div class="card-title">Document Q&A</div><p class="card-description">Ask direct questions about your document and get precise answers from the text itself.</p></div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
# In frontend/app.py

elif st.session_state.page == "login":
    st.title("Welcome to LexiLens AI")
    col1, col2 = st.columns(2, gap="large")

    # --- LOGIN FORM ---
    with col1:
        with st.form("login_form"):
            st.subheader("Login")
            email_login = st.text_input("Email")
            password_login = st.text_input("Password", type="password")
            
            submitted_login = st.form_submit_button("Login", use_container_width=True, type="primary")
            if submitted_login:
                # Send 'email_login' as the 'username' field, as expected by the backend
                login_data = {"username": email_login, "password": password_login}
                response = requests.post(f"{BACKEND_URL}/token", data=login_data)
                
                if response.status_code == 200:
                    st.session_state.token = response.json()["access_token"]
                    fetch_user_documents()
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Login failed: Invalid credentials.")

    # --- REGISTRATION FORM ---
    with col2:
        with st.form("register_form"):
            st.subheader("Don't have an account?")
            email_reg = st.text_input("Email ", key="reg_email")
            password_reg = st.text_input("Password ", type="password", key="reg_pass")
            
            submitted_reg = st.form_submit_button("Register", use_container_width=True)
            if submitted_reg:
                register_data = {"email": email_reg, "password": password_reg}
                response = requests.post(f"{BACKEND_URL}/register", data=register_data)

                if response.status_code == 201:
                    st.success("Registered successfully! Please login.")
                else:
                    st.error(f"Registration failed: {response.text}")

elif st.session_state.token:
    # Main app logic for logged-in users
    if st.session_state.page == "dashboard":
        st.title("Dashboard")
        if not st.session_state.uploaded_documents: fetch_user_documents()
        total_docs = len(st.session_state.uploaded_documents)
        col1, col2, col3 = st.columns(3, gap="large")
        with col1: st.markdown(f'<div class="card"><div class="card-icon">📄</div><div class="dashboard-metric">{total_docs}</div><div class="card-title">Total Documents</div></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div class="card"><div class="card-icon">🚨</div><div class="dashboard-metric">...</div><div class="card-title">High-Risk Docs</div></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div class="card"><div class="card-icon">✍️</div><div class="dashboard-metric">...</div><div class="card-title">Negotiations</div></div>', unsafe_allow_html=True)
        st.subheader("Your Documents")
        if not st.session_state.uploaded_documents:
            st.info("No documents found. Go to 'Upload & Analyze' to get started.")
        else:
            for doc_id, doc in st.session_state.uploaded_documents.items():
                col1, col2 = st.columns([4, 1])
                with col1: st.markdown(f"<div class='dashboard-doc-list'>📄 **{doc['title']}**</div>", unsafe_allow_html=True)
                with col2:
                    if st.button("View Analysis", key=f"dash_view_{doc_id}", use_container_width=True):
                        st.session_state.current_document_id = doc_id; st.session_state.page = "upload"; st.rerun()
    
    elif st.session_state.page == "upload":
        st.title("Upload & Analyze")
        if st.session_state.uploaded_documents:
            st.subheader("Previously Uploaded Documents")
            for doc_id, doc_info in list(st.session_state.uploaded_documents.items()):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1: st.write(f"📄 {doc_info['title']}")
                with col2:
                    if st.button("View", key=f"view_{doc_id}", use_container_width=True):
                        st.session_state.current_document_id = doc_id; st.rerun()
                with col3:
                    if st.button("Remove", key=f"remove_{doc_id}", use_container_width=True):
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        requests.delete(f"{BACKEND_URL}/documents/{doc_id}", headers=headers)
                        fetch_user_documents(); st.rerun()
            st.divider()
        st.subheader("Upload a New Document")
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'docx', 'txt'])
        if uploaded_file:
            if st.button("Analyze Document", type="primary", use_container_width=True):
                with st.spinner("Uploading and starting analysis..."):
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    response = requests.post(f"{BACKEND_URL}/analyze", files=files, headers=headers)
                    if response.status_code == 200:
                        st.success(response.json().get("message", "Analysis started!"))
                        time.sleep(1); fetch_user_documents(); st.rerun()
                    else:
                        st.error(f"Upload failed: {response.text}")
        st.divider()
        if st.session_state.current_document_id:
            doc_id = st.session_state.current_document_id
            if doc_id in st.session_state.uploaded_documents:
                doc_data = st.session_state.uploaded_documents[doc_id]
                if doc_data.get('analysis') is None: load_full_document_analysis(doc_id)
                display_analysis_results(doc_data.get('analysis'), doc_data['title'])

    elif st.session_state.page == "search":
        st.title("🔎 Document Q&A")
        st.write("Select a document and ask a specific question to find information within it.")
        if not st.session_state.uploaded_documents:
            st.warning("Please upload a document first.")
        else:
            doc_options = {doc_id: info['title'] for doc_id, info in st.session_state.uploaded_documents.items()}
            selected_doc_id = st.selectbox("Select a document:", options=list(doc_options.keys()), format_func=lambda doc_id: doc_options[doc_id])

            # Fetch suggestions if the document changes
            if selected_doc_id != st.session_state.last_suggestion_doc_id:
                fetch_suggestions(selected_doc_id)
                st.session_state.question_text = "" # Clear text area on doc change

            question = st.text_area("Your Question:", key="qa_question_input", value=st.session_state.question_text)
            st.session_state.question_text = question

            # Display suggestions as clickable buttons
            if st.session_state.suggestions and st.session_state.suggestions.get("qa_suggestions"):
                st.write("Suggestions:")
                cols = st.columns(3)
                for i, suggestion in enumerate(st.session_state.suggestions["qa_suggestions"]):
                    if cols[i % 3].button(suggestion, key=f"qa_sug_{i}"):
                        st.session_state.question_text = suggestion
                        st.rerun()
            if st.button("Ask Question", type="primary", use_container_width=True):
                if selected_doc_id and question:
                    with st.spinner("Searching for the answer..."):
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        payload = {"question": question}
                        response = requests.post(f"{BACKEND_URL}/document/{selected_doc_id}/query", json=payload, headers=headers)
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown('<div class="answer-box">', unsafe_allow_html=True)
                            st.write(result.get("answer", "No answer found."))
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.error(f"Q&A failed: {response.text}")

    elif st.session_state.page == "scenarios":
        st.title("🎭 What-If Scenario Analysis")
        st.write("Ask hypothetical questions about your documents to understand potential outcomes.")
        if not st.session_state.uploaded_documents:
            st.warning("Please upload a document first.")
        else:
            doc_options = {doc_id: info['title'] for doc_id, info in st.session_state.uploaded_documents.items()}
            selected_doc_id = st.selectbox("Select a document for the scenario:", options=list(doc_options.keys()), format_func=lambda doc_id: doc_options[doc_id])
            
            # Fetch suggestions if the document changes
            if selected_doc_id != st.session_state.last_suggestion_doc_id:
                fetch_suggestions(selected_doc_id)
                st.session_state.scenario_text = "" # Clear text area on doc change

            scenario_question = st.text_area("Describe your scenario:", key="scenario_question_input", value=st.session_state.scenario_text)
            st.session_state.scenario_text = scenario_question

            # Display suggestions as clickable buttons
            if st.session_state.suggestions and st.session_state.suggestions.get("scenario_suggestions"):
                st.write("Suggestions:")
                cols = st.columns(3)
                for i, suggestion in enumerate(st.session_state.suggestions["scenario_suggestions"]):
                    if cols[i % 3].button(suggestion, key=f"scen_sug_{i}"):
                        st.session_state.scenario_text = suggestion
                        st.rerun()
            
            if st.button("Analyze Scenario", type="primary", use_container_width=True):
                if selected_doc_id and scenario_question:
                    with st.spinner("AI is analyzing your scenario..."):
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        payload = {"scenario_text": scenario_question}
                        response = requests.post(f"{BACKEND_URL}/scenario/{selected_doc_id}", json=payload, headers=headers)
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown('<div class="answer-box">', unsafe_allow_html=True)
                            st.write(result.get("analysis", "Could not analyze scenario."))
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.error(f"Scenario analysis failed: {response.text}")
else:
    # Fallback for logged-out users on protected pages
    st.error("Please log in to access the application.")