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
        st.session_state.page = "home"
        st.rerun()

# Custom CSS
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
        # Dashboard Home
        st.header("Dashboard")
        st.markdown("Welcome to your LexiLens AI dashboard.")
        
        # Fetch user data from backend
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get("http://localhost:8000/user/documents", headers=headers)
        if response.status_code == 200:
            docs = response.json()
            st.metric("Documents Analyzed", len(docs))
        else:
            st.metric("Documents Analyzed", "0")
        
        # Mock other metrics
        st.metric("High-Risk Clauses Detected", "5")
        st.metric("API Calls Made", "28")
        st.metric("Reports Generated", "3")
        
        # Recent Documents
        st.subheader("Recent Documents")
        if response.status_code == 200:
            for doc in docs[-5:]:
                st.write(f"{doc['filename']} - Risk Score: {doc.get('risk_score', 'N/A')}")
        
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
                with st.spinner("Analyzing document..."):
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": uploaded_file.getvalue()}
                    response = requests.post("http://localhost:8000/analyze", files=files, headers=headers)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Analysis complete!")
                        st.json(result)
                    else:
                        st.error("Analysis failed. Please try again.")

elif st.session_state.page == "search":
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # Search & Explore
        st.header("Search & Explore")
        query = st.text_input("Enter search query")
        if st.button("Search") and query:
            with st.spinner("Searching documents..."):
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.post("http://localhost:8000/search", params={"query": query}, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    st.subheader(f"Search Results for: '{data['query']}'")
                    if data["results"]:
                        for result in data["results"]:
                            st.write(f"**{result['filename']}**")
                            st.write(result["snippet"])
                            st.divider()
                    else:
                        st.write("No results found.")
                else:
                    st.error("Search failed. Please try again.")

elif st.session_state.page == "scenarios":
    if not st.session_state.token:
        st.error("Please login first")
        st.session_state.page = "login"
    else:
        # What-If Scenarios
        st.header("What-If Scenarios")
        scenario = st.text_area("Describe your legal scenario")
        if st.button("Analyze Scenario") and scenario:
            with st.spinner("Analyzing scenario..."):
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.post("http://localhost:8000/scenario", params={"scenario": scenario}, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    st.subheader(f"Analysis for: '{data['scenario']}'")
                    st.write(data["analysis"])
                else:
                    st.error("Analysis failed. Please try again.")

# Footer
st.markdown("---")
st.markdown("© 2025 LexiLens AI. All rights reserved.")
