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
    if not st.session_state.token:
        return
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get("http://localhost:8000/user/documents", headers=headers)
        if response.status_code == 200:
            st.session_state.uploaded_documents = {} # Clear and resync
            for doc in response.json():
                doc_id = str(doc['id'])
                st.session_state.uploaded_documents[doc_id] = {
                    "title": doc.get('title', doc['filename']), # <-- UPDATED: Get title
                    "filename": doc['filename'],
                    "uploaded_at": doc.get('uploaded_at', ''),
                    "analysis": None
                }
    except Exception as e:
        print(f"Error fetching documents: {e}")

def load_full_document_analysis(doc_id):
    if not st.session_state.token or not doc_id:
        return
    try:
        with st.spinner(f"Loading analysis..."):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.get(f"http://localhost:8000/documents/{doc_id}", headers=headers)
            if response.status_code == 200:
                full_doc_data = response.json()
                st.session_state.uploaded_documents[doc_id]['analysis'] = full_doc_data.get('analysis')
    except Exception as e:
        st.error(f"An error occurred while loading analysis: {e}")

# --- UI Component Functions ---
def display_analysis_results(analysis_result, title): # <-- UPDATED: Use title
    if not analysis_result:
        st.warning("Analysis for this document is not available or still processing.")
        return

    st.subheader(f"📊 Analysis for: {title}") # <-- UPDATED: Use title
    # ... (rest of this function is the same) ...
    risk_score = analysis_result.get('overall_risk_score', 0)
    if risk_score <= 0.3: color, level = "green", "Low Risk"
    elif risk_score <= 0.7: color, level = "orange", "Medium Risk"
    else: color, level = "red", "High Risk"
    st.metric(label="Overall Risk Score", value=f"{risk_score:.2f}", delta=level)

    with st.expander("📝 Simplified Summary", expanded=True):
        st.write(analysis_result.get('simplified_summary', 'No summary provided.'))

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
        if st.button("What-If Scenarios", use_container_width=True): st.session_state.page = "scenarios"
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.uploaded_documents = {}
            st.session_state.current_document_id = None
            st.session_state.page = "home"
            st.rerun()

# Main Page Content
if st.session_state.page == "login":
    # ... (Login page code is the same) ...
    st.title("Welcome to LexiLens AI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True, type="primary"):
            response = requests.post("http://localhost:8000/token", data={"username": email, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json()["access_token"]
                fetch_user_documents()
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
        fetch_user_documents() # Fetch if empty

    if not st.session_state.uploaded_documents:
        st.info("No documents found. Go to the 'Upload & Analyze' page to get started.")
    else:
        st.metric("Total Documents Analyzed", len(st.session_state.uploaded_documents))
        st.subheader("Recent Documents")
        for doc_id, doc in st.session_state.uploaded_documents.items():
            with st.container():
                 # <-- UPDATED: Use title
                st.write(f"📄 **{doc['title']}** (File: {doc['filename']})")
                st.divider()

elif st.session_state.token and st.session_state.page == "upload":
    st.title("Upload & Analyze")

    if st.session_state.uploaded_documents:
        st.subheader("Your Previously Uploaded Documents")
        for doc_id, doc_info in st.session_state.uploaded_documents.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {doc_info['title']}") # <-- UPDATED: Use title
            with col2:
                if st.button("View Analysis", key=f"view_{doc_id}", use_container_width=True):
                    st.session_state.current_document_id = doc_id
        st.divider()

    st.subheader("Upload a New Document")
    uploaded_file = st.file_uploader("Choose a PDF, DOCX, or TXT file", type=['pdf', 'docx', 'txt'])

    if uploaded_file is not None:
        if st.button("Analyze Document", type="primary", use_container_width=True):
            # ... (File upload logic is the same) ...
            with st.spinner("Uploading and starting analysis..."):
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post("http://localhost:8000/analyze", files=files, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Analysis started!"))
                    st.info("The full analysis will be available here and on your dashboard shortly.")
                    time.sleep(2) # Give a moment for the background task to start
                    fetch_user_documents()
                    st.rerun()
                else:
                    st.error(f"Upload failed: {response.text}")
    
    st.divider()

    if st.session_state.current_document_id:
        doc_id = st.session_state.current_document_id
        if doc_id in st.session_state.uploaded_documents:
            doc_data = st.session_state.uploaded_documents[doc_id]
            if doc_data.get('analysis') is None:
                load_full_document_analysis(doc_id)
            
            display_analysis_results(doc_data.get('analysis'), doc_data['title']) # <-- UPDATED: Use title

elif st.session_state.token and st.session_state.page == "scenarios":
    st.title("🎭 What-If Scenario Analysis")
    st.write("Ask questions about your documents to understand potential outcomes.")

    if not st.session_state.uploaded_documents:
        st.warning("You need to upload at least one document.")
    else:
        # <-- UPDATED: Use title in selectbox
        doc_options = {doc_id: info['title'] for doc_id, info in st.session_state.uploaded_documents.items()}
        selected_doc_id = st.selectbox(
            "Select a document to base your scenario on:",
            options=list(doc_options.keys()),
            format_func=lambda doc_id: doc_options[doc_id]
        )

        scenario_question = st.text_area(
            "Describe your scenario or ask your question:",
            height=150,
            placeholder="e.g., What happens if I miss a payment deadline?"
        )

        if st.button("Analyze Scenario", type="primary", use_container_width=True):
            # ... (Scenario analysis logic is the same) ...
            if selected_doc_id and scenario_question:
                with st.spinner("AI is analyzing your scenario..."):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        api_url = f"http://localhost:8000/scenario/{selected_doc_id}"
                        payload = {"scenario_text": scenario_question}
                        response = requests.post(api_url, json=payload, headers=headers)

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
    # Fallback and Home page
    st.title("From Legal Chaos to Crystal Clarity.")
    st.subheader("The AI platform that deconstructs, classifies, and simplifies your contracts.")
    if st.button("Get Started for Free"):
        st.session_state.page = "login"
        st.rerun()