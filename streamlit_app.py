
import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="PerXL Voice Assistant",
    page_icon="🎙️",
    layout="wide"
)

DEFAULT_API_URL = "https://per-xl-voice-assistant.vercel.app"

st.title("🎙️ PerXL Voice Assistant")
st.caption("Streamlit Frontend connected to FastAPI Backend")

with st.sidebar:
    st.header("Backend Configuration")
    api_url = st.text_input(
        "FastAPI Base URL",
        value=DEFAULT_API_URL
    ).strip().rstrip("/")

    check_connection = st.button(
        "Check Backend Connection",
        use_container_width=True
    )

def get_api_data(endpoint):
    try:
        response = requests.get(
            f"{api_url}{endpoint}",
            timeout=30
        )
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError:
        return None, "The backend did not return valid JSON."

if check_connection:
    data, error = get_api_data("/health")
    if error:
        st.error(f"Backend connection failed: {error}")
    else:
        st.success("Backend connection successful!")
        st.json(data)

tab1, tab2, tab3 = st.tabs(
    ["Dashboard", "Task Data", "API Explorer"]
)

with tab1:
    st.subheader("Backend Overview")

    if st.button("Load Dashboard Data", type="primary"):
        endpoints = {
            "Health": "/health",
            "Task Summary": "/tasks/summary",
            "Tasks by Status": "/tasks/by-status",
            "Tasks by Priority": "/tasks/by-priority",
            "Collections": "/collections"
        }

        for name, endpoint in endpoints.items():
            with st.expander(name, expanded=True):
                data, error = get_api_data(endpoint)

                if error:
                    st.error(f"{endpoint}: {error}")
                else:
                    st.json(data)

with tab2:
    st.subheader("Task Data")

    task_view = st.selectbox(
        "Choose task information",
        [
            "Task Summary",
            "Tasks by Status",
            "Tasks by Priority"
        ]
    )

    endpoint_map = {
        "Task Summary": "/tasks/summary",
        "Tasks by Status": "/tasks/by-status",
        "Tasks by Priority": "/tasks/by-priority"
    }

    if st.button("Fetch Task Data"):
        data, error = get_api_data(endpoint_map[task_view])

        if error:
            st.error(error)
        elif isinstance(data, list) and data and all(
            isinstance(item, dict) for item in data
        ):
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.json(data)

with tab3:
    st.subheader("API Explorer")

    endpoint = st.selectbox(
        "Select an API endpoint",
        [
            "/health",
            "/collections",
            "/tasks/summary",
            "/tasks/by-status",
            "/tasks/by-priority",
            "/sections",
            "/spaces"
        ]
    )

    if st.button("Send API Request", type="primary"):
        data, error = get_api_data(endpoint)

        if error:
            st.error(f"Request failed: {error}")
        else:
            st.success("Request completed successfully.")
            st.json(data)

st.divider()
st.caption("PerXL Voice Assistant | FastAPI + Streamlit")
