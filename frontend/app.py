import streamlit as st
import requests
import time

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

# --- API Communication Functions ---
def fetch_user_documents():
    """Fetches the list of user documents from the backend and stores them in session state."""
    if not st.session_state.token:
        return
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get("http://localhost:8000/user/documents", headers=headers)
        if response.status_code == 200:
            for doc in response.json():
                doc_id = str(doc['id'])
                if doc_id not in st.session_state.uploaded_documents:
                    st.session_state.uploaded_documents[doc_id] = {
                        "filename": doc['filename'],
                        "uploaded_at": doc.get('uploaded_at', ''),
                        "analysis": None # Lazily load analysis
                    }
        else:
            # Clear local docs if token is invalid
            st.session_state.uploaded_documents = {}
    except requests.ConnectionError:
        st.error("Connection to backend failed. Is the server running?")
    except Exception as e:
        print(f"Error fetching documents: {e}")

def load_full_document_analysis(doc_id):
    """Fetches the full analysis for a specific document and updates the session state."""
    if not st.session_state.token or not doc_id:
        return
    try:
        with st.spinner(f"Loading analysis for document {doc_id}..."):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.get(f"http://localhost:8000/documents/{doc_id}", headers=headers)
            if response.status_code == 200:
                full_doc_data = response.json()
                st.session_state.uploaded_documents[doc_id]['analysis'] = full_doc_data.get('analysis')
            else:
                st.error(f"Failed to load analysis for document {doc_id}.")
    except Exception as e:
        st.error(f"An error occurred while loading analysis: {e}")

# --- UI Component Functions ---
def display_analysis_results(analysis_result, filename):
    """Renders the detailed analysis view."""
    if not analysis_result:
        st.warning("Analysis for this document is not available or still processing.")
        return

    st.subheader(f"📊 Analysis for: {filename}")

    # Overall Risk Score
    risk_score = analysis_result.get('overall_risk_score', 0)
    if risk_score <= 0.3: color, level = "green", "Low Risk"
    elif risk_score <= 0.7: color, level = "orange", "Medium Risk"
    else: color, level = "red", "High Risk"
    st.metric(label="Overall Risk Score", value=f"{risk_score:.2f}", delta=level)

    # Simplified Summary
    with st.expander("📝 Simplified Summary", expanded=True):
        st.write(analysis_result.get('simplified_summary', 'No summary provided.'))

    # High-Risk Clauses
    st.subheader("⚠️ High-Risk Clauses")
    high_risk_clauses = analysis_result.get('high_risk_clauses', [])
    if high_risk_clauses:
        for i, clause in enumerate(high_risk_clauses):
            with st.container():
                st.markdown(f"**Clause {i+1}:** {clause.get('clause', 'N/A')}")
                st.info(f"**Reason:** {clause.get('reason', 'N/A')}")
                st.progress(clause.get('confidence', 0.0), text=f"Confidence: {clause.get('confidence', 0.0):.0%}")
                st.divider()
    else:
        st.success("No high-risk clauses were detected.")

# --- Page Rendering Logic ---

# Sidebar Navigation
with st.sidebar:
    st.title("⚖️ LexiLens AI")
    if st.button("Home", use_container_width=True): st.session_state.page = "home"
    if not st.session_state.token:
        if st.button("Login / Register", use_container_width=True): st.session_state.page = "login"
    if st.session_state.token:
        if st.button("Dashboard", use_container_width=True): st.session_state.page = "dashboard"
        if st.button("Upload & Analyze", use_container_width=True): st.session_state.page = "upload"
        # ADDED: What-If Scenarios button in the sidebar
        if st.button("What-If Scenarios", use_container_width=True): st.session_state.page = "scenarios"
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.uploaded_documents = {}
            st.session_state.current_document_id = None
            st.session_state.page = "home"
            st.rerun()

# --- Main Page Content ---

if st.session_state.page == "home":
    st.title("From Legal Chaos to Crystal Clarity.")
    st.subheader("The AI platform that deconstructs, classifies, and simplifies your contracts.")
    if st.button("Get Started for Free"):
        st.session_state.page = "login"
        st.rerun()

elif st.session_state.page == "login":
    st.title("Welcome to LexiLens AI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True, type="primary"):
            response = requests.post("http://localhost:8000/token", data={"username": email, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json()["access_token"]
                fetch_user_documents() # Fetch docs immediately on login
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with col2:
        if st.button("Register", use_container_width=True):
            response = requests.post("http://localhost:8000/register", data={"email": email, "password": password})
            if response.status_code == 201:
                st.success("Registered successfully! Please login.")
            else:
                st.error(f"Registration failed: {response.text}")

elif st.session_state.token and st.session_state.page == "dashboard":
    st.title("Dashboard")
    st.write("Welcome back! Here's a summary of your documents.")

    if not st.session_state.uploaded_documents:
        st.info("No documents found. Go to the 'Upload & Analyze' page to get started.")
    else:
        st.metric("Total Documents Analyzed", len(st.session_state.uploaded_documents))
        st.subheader("Recent Documents")
        for doc_id, doc in st.session_state.uploaded_documents.items():
            with st.container():
                st.write(f"📄 **{doc['filename']}** (Uploaded: {doc.get('uploaded_at', 'N/A')})")
                st.divider()

elif st.session_state.token and st.session_state.page == "upload":
    st.title("Upload & Analyze")

    # --- Section for Previously Uploaded Documents ---
    if st.session_state.uploaded_documents:
        st.subheader("Your Previously Uploaded Documents")
        for doc_id, doc_info in st.session_state.uploaded_documents.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {doc_info['filename']}")
            with col2:
                if st.button("View Analysis", key=f"view_{doc_id}", use_container_width=True):
                    st.session_state.current_document_id = doc_id
                    # The analysis will be loaded and displayed below
        st.divider()

    # --- File Uploader ---
    st.subheader("Upload a New Document")
    uploaded_file = st.file_uploader("Choose a PDF, DOCX, or TXT file", type=['pdf', 'docx', 'txt'])

    if uploaded_file is not None:
        if st.button("Analyze Document", type="primary", use_container_width=True):
            with st.spinner("Uploading and starting analysis... This may take a moment."):
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post("http://localhost:8000/analyze", files=files, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Analysis started!"))
                    st.info("The full analysis will be available here and on your dashboard shortly.")
                    # Refresh the document list to include the new one
                    fetch_user_documents()
                else:
                    st.error(f"Upload failed: {response.text}")

    st.divider()

    # --- Display Selected Document's Analysis ---
    if st.session_state.current_document_id:
        doc_id = st.session_state.current_document_id
        if doc_id in st.session_state.uploaded_documents:
            doc_data = st.session_state.uploaded_documents[doc_id]
            # Lazily load the analysis if it's not already present
            if doc_data.get('analysis') is None:
                load_full_document_analysis(doc_id)

            display_analysis_results(doc_data.get('analysis'), doc_data['filename'])

# --- ADDED: WHAT-IF SCENARIOS PAGE ---
# In frontend/app.py

elif st.session_state.token and st.session_state.page == "scenarios":
    st.title("🎭 What-If Scenario Analysis")
    st.write("Ask questions about your documents to understand potential outcomes.")

    if not st.session_state.uploaded_documents:
        st.warning("You need to upload at least one document to analyze a scenario.")
        if st.button("Go to Upload Page"):
            st.session_state.page = "upload"
            st.rerun()
    else:
        # Create a list of document options for the selectbox
        doc_options = {doc_id: info['filename'] for doc_id, info in st.session_state.uploaded_documents.items()}
        selected_doc_id = st.selectbox(
            "Select a document to base your scenario on:",
            options=list(doc_options.keys()), # Ensure options is a list
            format_func=lambda doc_id: doc_options[doc_id]
        )

        scenario_question = st.text_area(
            "Describe your scenario or ask your question:",
            height=150,
            placeholder="e.g., What happens if the client terminates the contract after 6 months?\nWhat are my obligations if a payment is delayed?"
        )

        if st.button("Analyze Scenario", type="primary", use_container_width=True):
            if selected_doc_id and scenario_question:
                with st.spinner("AI is analyzing your scenario..."):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        
                        # CORRECTED: Construct the URL with the document ID
                        api_url = f"http://localhost:8000/scenario/{selected_doc_id}"
                        
                        # CORRECTED: Send the scenario text in the JSON body
                        payload = {"scenario_text": scenario_question}

                        response = requests.post(
                            api_url,
                            json=payload, # Use json= to send application/json
                            headers=headers
                        )
                        if response.status_code == 200:
                            result = response.json()
                            st.subheader("AI-Powered Scenario Analysis")
                            st.markdown(result.get("analysis", "No analysis could be generated."))
                        else:
                            st.error(f"Scenario analysis failed: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.warning("Please select a document and describe your scenario.")

else:
    # Fallback for logged-out users trying to access protected pages
    st.error("Please log in to access this page.")
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()