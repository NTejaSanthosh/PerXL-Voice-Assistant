
import streamlit as st
import requests

st.set_page_config(
    page_title="PerXL Voice Assistant",
    page_icon="🎙️",
    layout="wide"
)

st.title("🎙️ PerXL Voice Assistant")
st.caption("Voice-enabled assistant with FastAPI backend")

api_url = st.sidebar.text_input(
    "Backend API URL",
    value="https://per-xl-voice-assistant.vercel.app"
)

st.sidebar.info("Connect this dashboard to your deployed backend API.")

tab1, tab2, tab3 = st.tabs([
    "Assistant",
    "API Health",
    "About"
])

with tab1:
    st.subheader("Ask the PerXL Assistant")
    question = st.text_area(
        "Enter your question",
        placeholder="Type your question here..."
    )

    if st.button("Send Question", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            st.info(
                "The dashboard is ready, but the backend request needs "
                "to be connected to the correct API endpoint."
            )
            st.code(question)

with tab2:
    st.subheader("Backend Connectivity")

    if st.button("Check Backend"):
        try:
            response = requests.get(
                api_url.rstrip("/") + "/",
                timeout=15
            )
            st.write("HTTP status:", response.status_code)
            st.code(response.text[:3000])
        except requests.RequestException as exc:
            st.error(f"Backend connection failed: {exc}")

with tab3:
    st.subheader("About PerXL Voice Assistant")
    st.write(
        "PerXL Voice Assistant is a voice-enabled assistant with a "
        "FastAPI backend and frontend interface."
    )
    st.write(
        "This Streamlit interface is an additional dashboard. "
        "The actual question-answering endpoint must be connected "
        "to enable assistant responses."
    )
