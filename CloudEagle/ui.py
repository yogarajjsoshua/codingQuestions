"""
Streamlit UI for Country Information AI Agent

Run this with: streamlit run ui.py
Make sure the FastAPI backend is running on http://localhost:8000
"""

import streamlit as st
import requests
import time
import os
from typing import Optional

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Country Info AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# Custom CSS - Minimalist Design
st.markdown("""
    <style>
    /* Import Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main {
        background: #ffffff;
        padding: 0;
    }
    
    /* Dark mode */
    .dark-mode .main {
        background: #1a1a1a;
    }
    
    /* Chat container */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 60px 24px 120px 24px;
    }
    
    /* Header */
    .app-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(0, 0, 0, 0.06);
        padding: 16px 24px;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .dark-mode .app-header {
        background: rgba(26, 26, 26, 0.8);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .app-title {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0;
        letter-spacing: -0.3px;
    }
    
    .dark-mode .app-title {
        color: #ffffff;
    }
    
    /* Message bubbles */
    .message {
        display: flex;
        margin-bottom: 32px;
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .message-content {
        flex: 1;
        line-height: 1.6;
        background: transparent;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px;
    }
    
    .dark-mode .message-content {
        border: 1px solid #374151;
    }
    
    .message-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 16px;
        flex-shrink: 0;
        font-size: 16px;
        border: 1px solid #E5E7EB;
    }
    
    .dark-mode .message-avatar {
        border: 1px solid #374151;
    }
    
    .user-message .message-avatar {
        background: transparent;
        border-color: #3B82F6;
    }
    
    .assistant-message .message-avatar {
        background: transparent;
        border-color: #10B981;
    }
    
    .message-text {
        color: #374151;
        font-size: 15px;
        font-weight: 400;
        line-height: 1.7;
    }
    
    .dark-mode .message-text {
        color: #D1D5DB;
    }
    
    .message-label {
        font-size: 13px;
        font-weight: 600;
        color: #6B7280;
        margin-bottom: 8px;
        letter-spacing: 0.3px;
    }
    
    .dark-mode .message-label {
        color: #9CA3AF;
    }
    
    /* Metadata */
    .message-metadata {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(229, 231, 235, 0.5);
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        font-size: 12px;
        color: #6B7280;
    }
    
    .dark-mode .message-metadata {
        border-top: 1px solid rgba(55, 65, 81, 0.5);
        color: #9CA3AF;
    }
    
    .metadata-item {
        display: flex;
        align-items: center;
        gap: 4px;
        background: transparent;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(229, 231, 235, 0.5);
    }
    
    .dark-mode .metadata-item {
        border: 1px solid rgba(55, 65, 81, 0.5);
    }
    
    /* Input area */
    .stChatInputContainer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(0, 0, 0, 0.06);
        padding: 20px;
        z-index: 1000;
    }
    
    .dark-mode .stChatInputContainer {
        background: rgba(26, 26, 26, 0.8);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stChatInput {
        max-width: 900px;
        margin: 0 auto;
    }
    
    .stChatInput > div {
        border-radius: 12px;
        border: 1px solid #E5E7EB !important;
        background: transparent !important;
    }
    
    .dark-mode .stChatInput > div {
        border: 1px solid #374151 !important;
        background: transparent !important;
    }
    
    .stChatInput textarea {
        font-size: 15px;
        color: #ffffff !important;
        background: transparent !important;
    }
    
    .dark-mode .stChatInput textarea {
        color: #ffffff !important;
        background: transparent !important;
    }
    
    /* Make send button icon visible */
    .stChatInput button {
        background: #3B82F6 !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        border: 1px solid #3B82F6 !important;
    }
    
    .stChatInput button:hover {
        background: #2563EB !important;
        border-color: #2563EB !important;
    }
    
    .stChatInput button svg {
        fill: #ffffff !important;
        width: 20px !important;
        height: 20px !important;
    }
    
    .dark-mode .stChatInput button {
        background: #3B82F6 !important;
        border: 1px solid #3B82F6 !important;
    }
    
    .dark-mode .stChatInput button:hover {
        background: #2563EB !important;
        border-color: #2563EB !important;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 14px;
        border: 1px solid #E5E7EB !important;
        background: transparent !important;
        color: #374151;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background: rgba(243, 244, 246, 0.3) !important;
        border-color: #D1D5DB !important;
    }
    
    .dark-mode .stButton button {
        border: 1px solid #374151 !important;
        background: transparent !important;
        color: #D1D5DB;
    }
    
    .dark-mode .stButton button:hover {
        background: rgba(55, 65, 81, 0.3) !important;
        border-color: #4B5563 !important;
    }
    
    /* Welcome screen */
    .welcome-screen {
        max-width: 700px;
        margin: 120px auto 0;
        text-align: center;
        padding: 0 24px;
    }
    
    .welcome-title {
        font-size: 42px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 12px;
        letter-spacing: -1px;
    }
    
    .dark-mode .welcome-title {
        color: #ffffff;
    }
    
    .welcome-subtitle {
        font-size: 18px;
        color: #6B7280;
        margin-bottom: 48px;
        font-weight: 400;
    }
    
    .dark-mode .welcome-subtitle {
        color: #9CA3AF;
    }
    
    .example-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-top: 32px;
    }
    
    .example-card {
        background: transparent;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .example-card:hover {
        background: rgba(243, 244, 246, 0.3);
        border-color: #D1D5DB;
        transform: translateY(-2px);
    }
    
    .dark-mode .example-card {
        background: transparent;
        border: 1px solid #374151;
    }
    
    .dark-mode .example-card:hover {
        background: rgba(55, 65, 81, 0.3);
        border-color: #4B5563;
    }
    
    .example-text {
        font-size: 14px;
        color: #374151;
        font-weight: 500;
    }
    
    .dark-mode .example-text {
        color: #D1D5DB;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #3B82F6 transparent transparent transparent !important;
    }
    
    /* Error messages */
    .stAlert {
        border-radius: 12px;
        border: none;
        max-width: 900px;
        margin: 16px auto;
    }
    
    /* Settings button */
    .settings-btn {
        position: fixed;
        top: 16px;
        right: 24px;
        z-index: 1001;
    }
    </style>
""", unsafe_allow_html=True)


def check_backend_health() -> bool:
    """Check if the backend API is accessible."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def query_country_info(question: str) -> dict:
    """Send a query to the backend API with session context."""
    try:
        payload = {"question": question}
        
        # Include session_id if it exists for conversation continuity
        if st.session_state.session_id:
            payload["session_id"] = st.session_state.session_id
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/query",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": "Country not found. Please check the country name."}
        elif e.response.status_code == 429:
            return {"success": False, "error": "Rate limit exceeded. Please wait a moment and try again."}
        else:
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            return {"success": False, "error": f"Error: {error_detail}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to backend. Make sure the API is running on port 8000."}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. Please try again."}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# Apply dark mode class
dark_mode_class = "dark-mode" if st.session_state.dark_mode else ""
st.markdown(f'<div class="{dark_mode_class}">', unsafe_allow_html=True)

# Header
st.markdown(f"""
    <div class="app-header">
        <h1 class="app-title">🌍 Country Information AI</h1>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 12px; color: {'#10B981' if st.session_state.session_id else '#9CA3AF'}; font-weight: 500;">
                {'🟢 Context Active' if st.session_state.session_id else '⚪ New Session'}
            </span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Settings in top right
col1, col2, col3 = st.columns([6, 1, 1])
with col2:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
with col3:
    if st.button("🗑️"):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()

# Main content
if not st.session_state.messages:
    # Welcome screen
    st.markdown("""
        <div class="welcome-screen">
            <h1 class="welcome-title">What would you like to know?</h1>
            <p class="welcome-subtitle">Ask me anything about countries around the world. I remember our conversation!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Example questions
    example_col1, example_col2 = st.columns(2)
    examples = [
        "What is the population of Germany?",
        "What currency does Japan use?",
        "Tell me about France's geography",
        "What is its capital?",
    ]
    
    st.markdown('<div class="example-grid">', unsafe_allow_html=True)
    for i, example in enumerate(examples):
        st.markdown(f'<div class="example-card"><div class="example-text">💭 {example}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # Chat history
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"""
                <div class="message user-message">
                    <div class="message-avatar">👤</div>
                    <div class="message-content">
                        <div class="message-label">You</div>
                        <div class="message-text">{content}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            metadata = message.get("metadata", {})
            metadata_html = ""
            
            if metadata and any(metadata.values()):
                metadata_parts = []
                if metadata.get("country"):
                    metadata_parts.append(f'<span class="metadata-item">📍 {metadata["country"]}</span>')
                if metadata.get("fields_retrieved"):
                    fields = ", ".join(metadata["fields_retrieved"][:3])
                    if len(metadata["fields_retrieved"]) > 3:
                        fields += f" +{len(metadata['fields_retrieved']) - 3} more"
                    metadata_parts.append(f'<span class="metadata-item">📊 {fields}</span>')
                if metadata.get("execution_time_ms"):
                    metadata_parts.append(f'<span class="metadata-item">⏱️ {metadata["execution_time_ms"]:.0f}ms</span>')
                
                if metadata_parts:
                    metadata_html = f'<div class="message-metadata">{" ".join(metadata_parts)}</div>'
            
            st.markdown(f"""
                <div class="message assistant-message">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-label">AI Assistant</div>
                        <div class="message-text">{content}</div>
                        {metadata_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Chat input
question = st.chat_input("Ask a question about any country...")

if question:
    # Check backend
    if not check_backend_health():
        st.error("⚠️ Cannot connect to backend API. Make sure it's running on http://localhost:8000")
        st.stop()
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Query backend
    with st.spinner("Thinking..."):
        result = query_country_info(question)
    
    # Process response
    if result["success"]:
        data = result["data"]
        answer = data.get("answer", "No answer generated")
        
        # Save session_id for conversation continuity
        if "session_id" in data:
            st.session_state.session_id = data["session_id"]
        
        metadata = {
            "country": data.get("country"),
            "fields_retrieved": data.get("fields_retrieved", []),
            "execution_time_ms": data.get("execution_time_ms", 0),
            "session_id": data.get("session_id")
        }
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "metadata": metadata
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ {result['error']}",
            "metadata": {}
        })
    
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
